import sys
import inspect
import re
import logging
import os
import json
import pprint
import numpy as np
from datetime import datetime
from numpy import random
from functools import wraps

log_original = False

gamma_path = os.path.join(os.path.dirname(__file__), '..', '..', 'gamma')
config_file = os.path.join(gamma_path, 'config.json')
with open(config_file, 'r', encoding='utf-8') as f:
    info_list, person_trans_mat, state_trans_mat = json.load(f).values()
    
count = 0
number = 8
person = 'mutsumi'
state = 'random'
    
# 配置日志

class Fold:
    def __matmul__(self, content):
        if isinstance(content, str):
            return content.replace('\n', '\n    ')
        else:
            return pprint.pformat(content)
    
fold = Fold()

def define_custom_levels(level_num, level_name, method_name = None):
    """
    批量定义自定义日志级别并添加到Logger类
    :param level_definitions: list of tuples - 格式 [(level_num, level_name, method_name), ...]
                             或 [(level_num, level_name), ...] (自动生成方法名)
    """
    # 参数解析
    if method_name is None:
        method_name = level_name.lower()  # 默认使用小写的级别名称作为方法名
    
    # 检查级别冲突
    existing_level = logging.getLevelName(level_num)
    if existing_level != f"Level {level_num}":
        raise ValueError(f"Level number {level_num} already in use by: {existing_level}")
    
    if logging.getLevelName(level_name) != f"Level {level_name}":
        raise ValueError(f"Level name {level_name} already registered")

    # 注册级别名称
    logging.addLevelName(level_num, level_name)
    
    # 创建日志方法
    def make_log_method(level):
        def log_method(self, msg, *args, **kwargs):
            if self.isEnabledFor(level):
                self._log(level, msg, args, **kwargs)
        return log_method
    
    # 添加方法到Logger类（避免重复添加）
    if not hasattr(logging.Logger, method_name):
        setattr(logging.Logger, method_name, make_log_method(level_num))
            

# 1. 定义自定义级别数值和名称
define_custom_levels(25, 'NOTICE')
    
logger = logging.getLogger(__name__)
logger.setLevel(25)

file_path = os.path.join(gamma_path, 'logging', str(datetime.now()).replace(' ', '-').replace('.', '-').replace(':', '-') + '.log')
open(file_path, 'w', encoding='utf-8').close()

fh = logging.FileHandler(
    filename=file_path,
    mode='a',
    encoding='utf-8'
)
fh.setLevel(logging.NOTSET)
datefmt = '%Y-%m-%d %H:%M:%S'
format_str = '%(levelname)s - %(asctime)s - %(message)s'
formatter = logging.Formatter(format_str, datefmt)
fh.setFormatter(formatter)
logger.addHandler(fh)


def generate_next_person_info():
    global count, number, person, state
    if count == number:
        count = 0
        number = random.choice(
            [6, 8, 10, 12, 14, 16, 18],
            p = [0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05]
        )
        state = random.choice(['chaos', 'random', 'peace'], p=state_trans_mat[state])
    
    count += 1
    person = random.choice(['mutsumi', 'mortis'], p=person_trans_mat[state][person])
    logger.warning(fold @ f'Variables: count: {count}, number: {number}, person: {person}, state: {state}')

# +++ 新增prompt修改函数 +++    

def modify_prompt(original_prompt, func_name, gernerate_next = False, logger_level = logger.info):
    if any(pattern in original_prompt for pattern in info_list['mutsumi'].keys()):
        prompt = original_prompt
        if '<g_name>(ta的id:1373116809)'in prompt:
            prompt = prompt.replace('<g_name>(ta的id:1373116809)', '若叶睦(ta的id:1373116809)')
        if '推测你的日程安排，包括你一天都在做什么，从起床到睡眠' in original_prompt:
            prompt = prompt.replace('<g_name>', '若叶睦')
            
        if gernerate_next:
            generate_next_person_info()
        for key, value in info_list[person].items():
            prompt = prompt.replace(key, value)
            
        if log_original:
            logger_level( fold @
                f"Prompt modified in {func_name}\n"
                f"Original: {fold @ original_prompt}\n"
                f"Modified: {fold @ prompt}"
            )
        else:
            logger_level(fold @ f"Prompt modified in {func_name}\n{prompt}")
        return prompt
    else:
        return original_prompt
    

# +++ 新增输出修改函数 +++
def modify_output(original_output, func_name, enabled = False, logger_level = logger.info):
    if enabled and isinstance(original_output, str):
        output = f"{person}：{original_output}"
    else:
        output = original_output
        
    if log_original and enabled and isinstance(original_output, str):
        logger_level( fold @
            f"Output modified in {func_name}\n"
            f"Original: {fold @ original_output}\n"
            f"Modified: {fold @ output}"
        )
    else:
        logger_level(f"Output in {func_name}\n {fold @ output}")

    return output

def log_prompt(func):
    """装饰器：记录并修改prompt参数"""
    
    # 公共记录逻辑（只需维护这一处）
    def before_func(*args, **kwargs):
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        
        # +++ 新增prompt修改逻辑 +++
        if 'prompt' in bound_args.arguments:
        # 获取原始prompt
            prompt = bound_args.arguments.get('prompt', None)
            prompt = modify_prompt(prompt, func.__qualname__)
            bound_args.arguments['prompt'] = prompt
            
            
        return bound_args
    
    @wraps(func)
    async def async_wrapped(*args, **kwargs):
        bound_args = before_func(*args, **kwargs)  # 共用逻辑
        # === 执行原始函数 ===
        result = await func(*bound_args.args, **bound_args.kwargs)
        return modify_output(result, func.__qualname__)
    @wraps(func)
    def sync_wrapped(*args, **kwargs):
        bound_args = before_func(*args, **kwargs)  # 共用逻辑
        result = func(*bound_args.args, **bound_args.kwargs)
        return modify_output(result, func.__qualname__)

    # 自动选择包装器类型
    return async_wrapped if inspect.iscoroutinefunction(func) else sync_wrapped

def patch_classes(project_path):
    """
    动态修补所有项目模块中符合条件的类方法
    :param project_path: 项目根目录路径，用于过滤模块
    """
    for module in list(sys.modules.values()):
        # 跳过无文件或非项目模块
        if not (hasattr(module, '__file__') and module.__file__):
            continue
        if 'site-packages' in module.__file__:
            continue
        if not module.__file__.startswith(project_path):
            continue

        # 遍历模块中的属性（添加异常处理）
        for attr_name in dir(module):
            try:
                attr = getattr(module, attr_name)
            except AttributeError:
                continue  # 跳过无法访问的属性

            if inspect.isclass(attr):
                # 遍历类成员
                for method_name in dir(attr):
                    try:
                        method = getattr(attr, method_name)
                    except AttributeError:
                        continue  # 跳过无法访问的方法

                    if callable(method):
                        # 解开装饰器链找到原始方法
                        original_method = method
                        while hasattr(original_method, '__wrapped__'):
                            original_method = original_method.__wrapped__
                        
                        # 新增关键过滤条件
                        if (
                            # 排除内置方法
                            not inspect.isbuiltin(original_method)
                            # 排除类本身（如type）
                            and not isinstance(original_method, type)
                            # 排除无法获取源代码的方法
                            and inspect.isfunction(original_method)
                        ):
                            try:
                                # 安全获取签名
                                sig = inspect.signature(original_method)
                            except ValueError:
                                continue
                            
                            if 'prompt' in sig.parameters:
                                # 应用装饰器并替换方法
                                wrapped_method = log_prompt(original_method)
                                setattr(attr, method_name, wrapped_method)
                                logger.debug(fold @ f"Patched: {attr.__name__}.{method_name}")


print('[Gamma] Gamma Module Loaded')
# 使用示例：在程序入口调用，传入项目路径
if __name__ == "__main__":
    patch_classes(r"C:\Users\13731\Desktop\Projects\MaiMBot\MaiM-with-u\MaiBot")
    # 之后导入其他模块或启动应用