import os

from dotenv import load_dotenv

# Load environment variables from a .env file securely
load_dotenv()


class CredentialVault:
    """
    Enterprise-grade security pattern for credential vaulting.
    This ensures that the LLM only outputs JSON tool calls (Execution Isolation),
    and the Python backend securely injects the necessary keys to execute the request.
    API keys are NEVER passed to the LLM directly in the prompt or context.
    """

    @staticmethod
    def get_secret(key_name: str, default: str = None) -> str:
        """
        Retrieves a secret securely from the vault/environment.

        Args:
            key_name (str): The name of the environment variable (e.g., 'OPENAI_API_KEY').
            default (str, optional): Default value if the key is not found.

        Returns:
            str: The secret value.
        """
        secret = os.getenv(key_name, default)
        if not secret:
            print(
                f"[VAULT WARNING] Secret '{key_name}' was requested but not found in the environment."
            )
        return secret

    @staticmethod
    def require_secret(key_name: str) -> str:
        """
        Retrieves a secret securely, raising an error if it is not found.
        """
        secret = os.getenv(key_name)
        if not secret:
            raise ValueError(
                f"CRITICAL: Required secret '{key_name}' is missing from the Credential Vault."
            )
        return secret
