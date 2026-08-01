"""Configurações da aplicação, lidas a partir de variáveis de ambiente."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SECRET_KEY_INSEGURA = "dev-insecure-secret-change-me"


class Settings(BaseSettings):
    """Configurações centrais do projeto."""

    anthropic_api_key: str = Field(default="", min_length=1, description="Chave da API Anthropic (obrigatória para uso real)")
    database_url: str = "sqlite:///./mentor.db"
    claude_model: str = "claude-haiku-4-5"
    claude_model_analise: str | None = Field(
        default=None,
        description=(
            "Modelo para extração do perfil ao final da triagem (tarefa determinística, "
            "temperature=0). Se vazio, usa CLAUDE_MODEL. Pode ser um modelo mais barato/"
            "rápido (ex.: claude-haiku-4-5)."
        ),
    )
    claude_model_geracao: str | None = Field(
        default=None,
        description=(
            "Modelo para gerar o PDI e o currículo (textos mais completos). Se vazio, usa "
            "CLAUDE_MODEL."
        ),
    )

    app_env: Literal["development", "production"] = Field(
        default="development",
        description="Ambiente de execução. Em 'production' a configuração é validada com mais rigor.",
    )
    secret_key: str = Field(
        default=SECRET_KEY_INSEGURA,
        min_length=10,
        description=(
            "Chave usada para assinar o cookie de sessão. Gere um valor forte em produção "
            '(ex.: python -c "import secrets; print(secrets.token_hex(32))")'
        ),
    )
    session_max_age: int = Field(default=60 * 60 * 8, description="Duração da sessão em segundos (padrão: 8h)")
    session_https_only: bool = Field(
        default=False,
        description=(
            "Se True, o cookie de sessão só é enviado por HTTPS (flag Secure). Deixe False em "
            "desenvolvimento local (HTTP); em produção, prefira True (ativado automaticamente "
            "quando app_env=production e este valor não for explicitamente sobrescrito)."
        ),
    )
    admin_emails: str = Field(
        default="",
        description=(
            "E-mails (separados por vírgula) com acesso ao painel de administração. "
            "Quem usa um desses e-mails é tratado como administrador."
        ),
    )
    invite_code: str = Field(
        default="",
        description=(
            "Código de convite exigido no cadastro. Se vazio (padrão), o cadastro é aberto. "
            "Em produção com link público, defina um valor para impedir que estranhos criem "
            "contas e consumam a cota da API."
        ),
    )
    rate_limit_ativo: bool = Field(
        default=True,
        description=(
            "Liga a limitação de requisições por IP (cadastro, login, triagem e gerações). "
            "Desative apenas em testes automatizados ou desenvolvimento local."
        ),
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def emails_admin(self) -> set[str]:
        """Conjunto de e-mails administradores (normalizados em minúsculas)."""
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @model_validator(mode="after")
    def _validar_producao(self) -> "Settings":
        """Em produção, exige uma SECRET_KEY forte e ativa o cookie Secure por padrão."""
        if self.app_env == "production":
            if self.secret_key == SECRET_KEY_INSEGURA:
                raise ValueError(
                    "SECRET_KEY não pode usar o valor padrão inseguro em produção. "
                    'Defina SECRET_KEY no ambiente (python -c "import secrets; print(secrets.token_hex(32))").'
                )
            # Em produção o cookie deve trafegar apenas por HTTPS, a menos que tenha sido
            # explicitamente sobrescrito (ex.: atrás de um proxy que termina o TLS).
            if "session_https_only" not in self.model_fields_set:
                self.session_https_only = True
        return self


@lru_cache
def get_settings() -> Settings:
    """Retorna as configurações da aplicação (com cache)."""
    return Settings()
