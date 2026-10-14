"""Schemas da API — pitch do desenvolvedor e busca de similares."""

from typing import List, Optional

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class GamePitchInput(BaseModel):
    """
    O que o desenvolvedor informa ANTES do lançamento. Só o necessário para achar
    jogos parecidos e os gêneros de referência. Campos extras do formulário antigo
    (categorias, flags, ano…) são ignorados em vez de quebrar o frontend.
    """

    model_config = ConfigDict(populate_by_name=True, extra="ignore")

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
    genres: List[str] = Field(..., min_length=1)
    price_brl: Optional[float] = Field(None, ge=0, description="Preço planejado (opcional)")
    top_k: Optional[int] = Field(None, ge=1, le=20, description="Quantos jogos similares usar")


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
