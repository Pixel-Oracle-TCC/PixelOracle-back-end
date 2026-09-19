"""Schemas da API — pitch pré-lançamento e respostas de triangulação."""

from typing import Any, Dict, List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class GamePitchInput(BaseModel):
    """
    Dados que o desenvolvedor informa ANTES do lançamento.
    Não inclui reviews, notas de usuários nem vendas reais.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    titulo: str = Field(
        ...,
        min_length=1,
        max_length=200,
        validation_alias=AliasChoices("titulo", "name"),
        description="Título do jogo",
    )
    descricao: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        validation_alias=AliasChoices("descricao", "ideia", "description"),
        description="Descrição da ideia / proposta do jogo",
    )

    price_brl: float = Field(..., ge=0, description="Preço planejado em reais (BRL)")
    genres: List[str] = Field(..., min_length=1)
    categories: List[str] = Field(..., min_length=1)
    release_year: int = Field(..., ge=1990, le=2035, description="Ano planejado de lançamento")
    period_time: Optional[str] = Field(None, description="Opcional; derivado do ano se omitido")

    platforms: int = Field(1, ge=0)
    supported_languages: int = Field(1, ge=0)
    dlc: int = Field(0, ge=0)
    achievements: int = Field(0, ge=0, description="Conquistas planejadas na página Steam")
    metacritic: int = Field(0, ge=0, description="Use 0 — jogo ainda sem nota Metacritic")
    required_age_num: float = Field(0, ge=0)

    singleplayer: bool = True
    multiplayer: bool = False
    is_online: bool = False
    indie: bool = True
    early_access: bool = False
    trading_cards: bool = False
    workshop: bool = False
    is_free: bool = False
    coming_soon: bool = True
    adult_content: bool = False

    controller_support: str = "none"
    type: str = "game"


class RetrieveSimilarInput(BaseModel):
    """Entrada mínima para busca de jogos similares."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: str = Field(
        ...,
        min_length=10,
        max_length=4000,
        validation_alias=AliasChoices("descricao", "ideia", "description"),
    )
    genres: List[str] = Field(..., min_length=1)
    top_k: Optional[int] = Field(None, ge=1, le=50)


class DashboardEvidence(BaseModel):
    model_config = ConfigDict(extra="allow")

    tipo: Optional[str] = None


class DashboardPoint(BaseModel):
    ponto: str
    evidencia: Dict[str, Any] = Field(default_factory=dict)


class TriangulationDashboard(BaseModel):
    pontos_fortes: List[DashboardPoint] = Field(default_factory=list)
    pontos_fracos: List[DashboardPoint] = Field(default_factory=list)
    oportunidades: List[DashboardPoint] = Field(default_factory=list)
    riscos: List[DashboardPoint] = Field(default_factory=list)
    jogos_similares: List[Dict[str, Any]] = Field(default_factory=list)
    insights_genero: List[Dict[str, Any]] = Field(default_factory=list)


GameDataInput = GamePitchInput
