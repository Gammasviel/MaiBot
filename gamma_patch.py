import sys
import inspect
import logging
import json
import pprint
from datetime import datetime
from typing import Union, Callable
from numpy import random
from pathlib import Path
from functools import wraps
from src.common.logger import get_module_logger


class ConfigLoader:
    def __init__(self):
        self.gamma_path: Path = self.get_gamma_path()
        self.gamma_path.mkdir(parents=True, exist_ok=True)
        self.config: dict = self.load_config()
        
    def get_gamma_path(self) -> Path:
        return Path(__file__).parents[2] / 'gamma'
    
    def __truediv__(self, key) -> Path:
        return self.gamma_path / key
    
    def load_config(self):
        config_file = self / 'config.json'
        with open(config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    @property
    def info_list(self):
        return self.config["info_list"]
    
    @property
    def persona_trans_mat(self):
        return self.config["persona_trans_mat"]
    
    @property
    def mood_trans_mat(self):
        return self.config["mood_trans_mat"]

config = ConfigLoader()



class CustomFormatter(logging.Formatter):
    def formatTime(self, record, datefmt = None):
        ct = datetime.fromtimestamp(record.created)
        if datefmt:
            return ct.strftime(datefmt)
        else:
            return super().formatTime(record, datefmt)



class CustomLogger:
    def __init__(self):
        self.setup_custom_levels({25: 'NOTICE'})
        self.logger: logging.Logger = self.configure_logger()
        
    
    def setup_custom_levels(self, custom_levels):
        for level_num, level_name in custom_levels.items():
            self.define_custom_level(level_num, level_name)
    
    @staticmethod
    def define_custom_level(level_num: int, level_name: str, method_name: Union[None, str] = None):
        if method_name is None:
            method_name = level_name.lower()
            
        existing_level = logging.getLevelName(level_num)
        if existing_level != f"Level {level_num}":
            raise ValueError(f"Level number {level_num} already in use by: {existing_level}")
        
        if logging.getLevelName(level_name) != f"Level {level_name}":
            raise ValueError(f"Level name {level_name} already registered")

        logging.addLevelName(level_num, level_name)
        
        def make_log_method(level):
            def log_method(self, msg, *args, **kwargs):
                if self.isEnabledFor(level):
                    self._log(level, msg, args, **kwargs)
            return log_method
        
        if not hasattr(logging.Logger, method_name):
            setattr(logging.Logger, method_name, make_log_method(level_num))
    
    @staticmethod
    def configure_logger() -> logging.Logger:
        logger = logging.getLogger('gamma_patch')
        logger.setLevel(25)
        
        (config / 'logging').mkdir(exist_ok=True)
        log_file = config / 'logging' / datetime.now().strftime('%Y-%m-%d-%H-%M-%S-%f.log')
        
        file_handler = logging.FileHandler(
            filename=log_file,
            mode='a',
            encoding='utf-8'
        )
        
        formatter = CustomFormatter(
            "%(levelname)s - %(asctime)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S.%f"
        )
        
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        
        return logger

class ContentFold:
    def __matmul__(self, content: Union[str, object]) -> str:
        if isinstance(content, str):
            return content.replace("\n", "\n    ")
        return pprint.pformat(content)

fold = ContentFold()
logger = CustomLogger().logger



class DualPersonalityManager:
    def __init__(self):
        self.cycle: int = 0
        self.max_cycle: int = 6
        self.persona: str = 'mutsumi'
        self.mood: str = 'random'
    
    def switch_persona(self):
        if self.cycle == self.max_cycle:
            self.cycle = 0
            self.max_cycle = random.choice(
                [6, 8, 10, 12, 14, 16, 18],
                p=[0.05, 0.1, 0.2, 0.3, 0.2, 0.1, 0.05]
            )
            self.mood = random.choice(
                ["chaos", "random", "peace"],
                p = config.mood_trans_mat[self.mood]
            )
        self.cycle += 1
        self.persona = random.choice(
            ['mutsumi', 'mortis'],
            p = config.persona_trans_mat[self.mood][self.persona]
        )
        logger.warning(fold @ f'Variables: cycle: {self.cycle}, max: {self.max_cycle}, persona: {self.persona}, mood: {self.mood}')
    
persona = DualPersonalityManager()



class PromptOutputManager:
    def __init__(self, log_original: bool = False):
        self.log_original: bool = log_original
    
    def log_prompt(self, prompt: str, func_name: str, log_level: int = 20, original_prompt: str = ''):
        if self.log_original:
            logger.log(log_level, fold @
                f"Prompt modified in {func_name}\n"
                f"Original: {fold @ original_prompt}\n"
                f"Modified: {fold @ prompt}"
            )
        else:
            logger.log(log_level, fold @ f"Prompt in {func_name}\n{prompt}")
    
    def contains_pattern(self, original_prompt: str) -> bool:
        return any(pattern in original_prompt for pattern in config.info_list['mutsumi'].keys())
    
    def modify_prompt(self, original_prompt: str, switch_persona: bool = False) -> str:
        prompt = original_prompt
        prompt = self.special_modification(prompt)
        
        if self.contains_pattern(prompt):
            if switch_persona:
                persona.switch_persona()
            for key, value in config.info_list[persona.persona].items():
                prompt = prompt.replace(key, value)
        
        return prompt
    
    def special_modification(self, original_prompt: str) -> str:
        prompt = original_prompt
        if '<g_name>(ta的id:1373116809)'in prompt:
            prompt = prompt.replace('<g_name>(ta的id:1373116809)', '若叶睦(ta的id:1373116809)')
        if '推测你的日程安排，包括你一天都在做什么，从起床到睡眠' in prompt:
            prompt = prompt.replace('<g_name>', '若叶睦')
        return prompt
    
    def modify_output(self, original_output: Union[str, object]) -> str:
        return f"{persona.persona}：{original_output}"
    
    def log_output(self, output: Union[str, object], func_name: str, log_level: int = 20, original_output: Union[str, object] = '') -> str:
        if self.log_original:
            logger.log(log_level, fold @
                f"Output modified in {func_name}\n"
                f"Original: {fold @ original_output}\n"
                f"Modified: {fold @ output}"
            )
        else:
            logger.log(log_level, fold @ f"Prompt in {func_name}\n {output}")

processor = PromptOutputManager()



class DecoratorHandler:
    def __init__(self, log_level: int = 20, switch_persona: bool = False):
        self.log_level = log_level
        self.switch_persona = switch_persona
        
    def decorator(self, func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            bound_args = self.process_arguments(func, *args, **kwargs)
            result = await func(*bound_args.args, **bound_args.kwargs)
            return self.process_output(result, func.__qualname__)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            bound_args = self.process_arguments(func, *args, **kwargs)
            result = func(*bound_args.args, **bound_args.kwargs)
            return self.process_output(result, func.__qualname__)
        
        return async_wrapper if inspect.iscoroutinefunction(func) else sync_wrapper
    
    def process_arguments(self, func: Callable, *args, **kwargs):
        sig = inspect.signature(func)
        bound_args = sig.bind(*args, **kwargs)
        bound_args.apply_defaults()
        
        if "prompt" in bound_args.arguments:
            original_prompt = bound_args.arguments["prompt"]
            if processor.contains_pattern(original_prompt):
                modified_prompt = self.process_prompt(original_prompt, func.__qualname__)
                bound_args.arguments["prompt"] = modified_prompt
        
        return bound_args
    
    def process_prompt(self, original_prompt: str, func_name: str) -> str:
        modified_prompt = processor.modify_prompt(original_prompt, switch_persona=self.switch_persona)
        processor.log_prompt(modified_prompt, func_name, log_level=self.log_level, original_prompt=original_prompt)
        return modified_prompt

    def process_output(self, original_output: Union[str, object], func_name: str, enabled_modification: bool = False) -> Union[str, object]:
        if isinstance(original_output, str) and enabled_modification:
            modified_output = processor.modify_output(original_output)
            processor.log_output(modified_output, func_name, log_level=self.log_level, original_output=original_output)
            return modified_output
        processor.log_output(original_output, func_name)
        return original_output

dec_handler = DecoratorHandler()



class ClassPatcher:
    def __init__(self, project_path: str):
        self.project_path = project_path
        self.patch_classes()
    
    def patch_classes(self):
        for module in list(sys.modules.values()):
            if self.not_patchable_module(module):
                continue
            for attr_name in dir(module):
                try:
                    attr = getattr(module, attr_name)
                except AttributeError:
                    continue
                
                if inspect.isclass(attr):
                    self.patch_methods(attr)
                    
    def patch_methods(self, attr):
        for method_name in dir(attr):
            try:
                method = getattr(attr, method_name)
            except AttributeError:
                continue
            
            if callable(method):
                original_method = method
                while hasattr(original_method, '__wrapped__'):
                    original_method = original_method.__wrapped__
                    
                if self.is_method_patchable(original_method):
                    try:
                        sig = inspect.signature(original_method)
                    except ValueError:
                        return
                    
                    if 'prompt' in sig.parameters:
                        wrapped_method = dec_handler.decorator(original_method)
                        setattr(attr, method_name, wrapped_method)
                        logger.debug(fold @ f"Patched: {attr.__name__}.{method_name}")
    
    def is_method_patchable(self, method):
        return (
            not inspect.isbuiltin(method) and
            not isinstance(method, type) and
            inspect.isfunction(method)
        )
    
    def not_patchable_module(self, module: str):
        return (
            not (hasattr(module, '__file__') and module.__file__) or
            'site-packages' in module.__file__ or
            not module.__file__.startswith(self.project_path)
        )



stream_logger = get_module_logger('gamma')
stream_logger.info('[Gamma] Gamma Module Loaded')