"""Script argument validator - prevents command injection"""
from typing import Dict, List, Tuple, Callable, Optional
import shlex
import re


class ScriptArgumentValidator:
    """Validates script arguments using whitelist approach"""
    
    # Argument definitions: arg_name -> (type, needs_value, validator_func)
    ALLOWED_ARGS: Dict[str, Tuple[str, bool, Optional[Callable]]] = {
        '--use-tmux': ('flag', False, None),
        '--timeout': ('int', True, lambda v: 0 < int(v) <= 7200),
        '--max-retries': ('int', True, lambda v: 0 <= int(v) <= 10),
        '--no-validate': ('flag', False, None),
        '--effort': ('choice', True, lambda v: v in ['low', 'medium', 'high']),
        '--output-format': ('choice', True, lambda v: v in ['json', 'jsonl']),
        '--docker-image': ('string', True, lambda v: re.match(r'^[\w\-\./]+:[\w\-\.]+$', v)),
    }
    
    def validate(self, args_string: str) -> Dict:
        """
        Validate script arguments string
        
        Returns:
            {
                'valid': True/False,
                'parsed_args': {...},
                'errors': [...]
            }
        """
        if not args_string or not args_string.strip():
            return {'valid': True, 'parsed_args': {}, 'errors': []}
        
        errors = []
        parsed_args = {}
        
        try:
            # Use shlex for safe parsing (prevents injection)
            tokens = shlex.split(args_string)
        except ValueError as e:
            return {
                'valid': False,
                'parsed_args': {},
                'errors': [f'Failed to parse arguments: {e}']
            }
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            # Check if it's a valid argument format
            if not token.startswith('--'):
                errors.append(f'Invalid argument format: {token}')
                i += 1
                continue
            
            # Extract arg name (support --arg=value format)
            if '=' in token:
                arg_name, arg_value = token.split('=', 1)
            else:
                arg_name = token
                arg_value = None
            
            # Check whitelist
            if arg_name not in self.ALLOWED_ARGS:
                errors.append(f'Unsupported argument: {arg_name}')
                i += 1
                continue
            
            arg_type, needs_value, validator = self.ALLOWED_ARGS[arg_name]
            
            # Extract argument value
            if needs_value:
                if arg_value is None:
                    if i + 1 >= len(tokens):
                        errors.append(f'Argument {arg_name} requires a value')
                        i += 1
                        continue
                    arg_value = tokens[i + 1]
                    i += 1
                
                # Type validation
                try:
                    if arg_type == 'int':
                        arg_value = int(arg_value)
                    elif arg_type == 'float':
                        arg_value = float(arg_value)
                    
                    # Custom validator function
                    if validator and not validator(arg_value):
                        errors.append(f'Invalid value for {arg_name}: {arg_value}')
                        i += 1
                        continue
                except ValueError:
                    errors.append(f'Argument {arg_name} expects {arg_type} type, got: {arg_value}')
                    i += 1
                    continue
            
            parsed_args[arg_name] = arg_value if needs_value else True
            i += 1
        
        return {
            'valid': len(errors) == 0,
            'parsed_args': parsed_args,
            'errors': errors
        }
    
    def build_safe_command(self, script_path: str, base_args: Dict, user_args: str) -> List[str]:
        """
        Build safe command list for subprocess
        
        Args:
            script_path: Script file path
            base_args: System-provided arguments (dataset, output, etc.)
            user_args: User input argument string
        
        Returns:
            Safe command list for subprocess.run(cmd_list, shell=False)
        """
        # Validate user arguments
        validation = self.validate(user_args)
        if not validation['valid']:
            raise ValueError(f"Argument validation failed: {validation['errors']}")
        
        # Build command list (do NOT use shell=True)
        cmd = ['python', script_path]
        
        # Add system arguments
        for key, value in base_args.items():
            cmd.append(f'--{key}')
            cmd.append(str(value))
        
        # Add user arguments
        for key, value in validation['parsed_args'].items():
            cmd.append(key)
            if value is not True:  # Not a flag argument
                cmd.append(str(value))
        
        return cmd
    
    def get_argument_definitions(self) -> List[Dict]:
        """
        Get argument definitions for frontend
        
        Returns:
            List of argument definitions with metadata
        """
        definitions = []
        
        for arg_name, (arg_type, needs_value, validator) in self.ALLOWED_ARGS.items():
            definition = {
                'name': arg_name,
                'type': arg_type,
                'description': f'Argument {arg_name}'
            }
            
            # Add type-specific metadata
            if arg_type == 'int' and validator:
                # Try to extract min/max from validator (not perfect but helpful)
                definition['min'] = 0
                definition['max'] = 7200 if 'timeout' in arg_name else 10
            elif arg_type == 'choice':
                # Extract choices from validator
                if 'effort' in arg_name:
                    definition['choices'] = ['low', 'medium', 'high']
                elif 'format' in arg_name:
                    definition['choices'] = ['json', 'jsonl']
            
            definitions.append(definition)
        
        return definitions


# Global validator instance
validator = ScriptArgumentValidator()
