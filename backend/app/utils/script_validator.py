"""Script parameter validator for secure command execution"""
import shlex
from typing import List


class ScriptValidator:
    """
    Validates and parses script arguments to prevent command injection
    
    Uses a whitelist approach for safe argument handling
    """
    
    # Whitelist of safe argument patterns
    SAFE_ARGS = {
        '--timeout',
        '--max-iterations',
        '--model',
        '--model-params',
        '--temperature',
        '--max-tokens',
        '--verbose',
        '-v',
        '--debug',
        '--output-format',
        '--no-cache',
        '--log-level'
    }
    
    def validate_and_parse_args(self, args_string: str) -> List[str]:
        """
        Validate and parse command-line arguments
        
        Args:
            args_string: String of command-line arguments
            
        Returns:
            List of validated argument tokens
            
        Raises:
            ValueError: If invalid or unsafe arguments are detected
        """
        if not args_string or not args_string.strip():
            return []
        
        # Parse using shlex to handle quoted strings properly
        try:
            tokens = shlex.split(args_string)
        except ValueError as e:
            raise ValueError(f"Invalid argument syntax: {e}")
        
        validated = []
        i = 0
        
        while i < len(tokens):
            token = tokens[i]
            
            # Check if it's a flag
            if token.startswith('-'):
                if token not in self.SAFE_ARGS:
                    raise ValueError(f"Unsafe or unknown argument: {token}")
                
                validated.append(token)
                
                # Check if this flag expects a value
                if not token.startswith('--no-') and i + 1 < len(tokens):
                    next_token = tokens[i + 1]
                    
                    # If next token is not a flag, it's a value
                    if not next_token.startswith('-'):
                        # Validate value doesn't contain shell metacharacters
                        if self._is_safe_value(next_token):
                            validated.append(next_token)
                            i += 1
                        else:
                            raise ValueError(
                                f"Unsafe value for {token}: {next_token}"
                            )
            else:
                raise ValueError(f"Unexpected positional argument: {token}")
            
            i += 1
        
        return validated
    
    def _is_safe_value(self, value: str) -> bool:
        """
        Check if a value is safe (no shell metacharacters)
        
        Args:
            value: The value to check
            
        Returns:
            True if safe, False otherwise
        """
        # Shell metacharacters to reject
        dangerous_chars = {';', '|', '&', '$', '`', '(', ')', '<', '>', '\n', '\r'}
        
        return not any(char in value for char in dangerous_chars)
    
    def build_safe_command(self, base_cmd: List[str], args_string: str) -> List[str]:
        """
        Build a safe command list for subprocess execution
        
        Args:
            base_cmd: Base command parts (e.g., ['python', 'script.py'])
            args_string: Additional arguments string
            
        Returns:
            Complete command list safe for subprocess.run()
        """
        validated_args = self.validate_and_parse_args(args_string)
        return base_cmd + validated_args
