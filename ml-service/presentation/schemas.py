"""Schemas de entrada/saída da API (Pydantic)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class GameDataInput(BaseModel):
    """Payload alinhado ao schema de database_steam_br.json / train.py."""

    price_brl: float = Field(..., ge=0, description="Preço em reais (ex: 11.39)")
    genres: List[str] = Field(..., min_length=1, description='Ex: ["Ação", "Indie"]')
    categories: List[str] = Field(
        ..., min_length=1, description='Ex: ["Um jogador", "Proezas Steam"]'
    )

    release_year: int = Field(..., ge=1990, le=2035)
    period_time: Optional[str] = Field(
        None, description='Opcional. Ex: "Pandêmico/Pós" ou "Pré-pandêmico"'
    )

    platforms: int = Field(1, ge=0)
    supported_languages: int = Field(1, ge=0)
    dlc: int = Field(0, ge=0)
    achievements: int = Field(0, ge=0)
    metacritic: int = Field(0, ge=0)
    required_age_num: float = Field(0, ge=0)

    singleplayer: bool = True
    multiplayer: bool = False
    is_online: bool = False
    indie: bool = True
    early_access: bool = False
    trading_cards: bool = False
    workshop: bool = False
    is_free: bool = False
    coming_soon: bool = False
    adult_content: bool = False

    controller_support: str = "none"
    type: str = "game"
    score_desc: str = "Mixed"

    total_positive: int = Field(0, ge=0)
    total_reviews: int = Field(0, ge=0)
    user_score: float = Field(0.0, ge=0, le=100)
    multiplicador_boxleiter: int = Field(30, ge=1)
