from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Path
from pydantic import BaseModel, conint, validator
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine
from models import ClassePersonagem, ItemMagico, Personagem, TipoItem

Base.metadata.create_all(bind=engine)

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =============================== #
# VALIDAÇÃO DE DADOS COM PYDANTIC #
# =============================== #
# usando encapsulamento pra validar dados


# CLASSE BASE PARA HERANÇA
class ItemMagicoBase(BaseModel):
    nome: str
    tipo: TipoItem
    forca: conint(ge=0, le=10) = 0
    defesa: conint(ge=0, le=10) = 0

    @validator("forca")
    def validar_forca_arma(cls, v, values):
        if "tipo" in values and values["tipo"] == TipoItem.ARMADURA and v != 0:
            raise ValueError("Itens do tipo Armadura devem ter força zero")
        return v

    @validator("defesa")
    def validar_defesa_armadura(cls, v, values):
        if "tipo" in values and values["tipo"] == TipoItem.ARMA and v != 0:
            raise ValueError("Itens do tipo Arma devem ter defesa zero")
        return v

    @validator("defesa")
    def validar_item_com_atributo(cls, v, values):
        if "forca" in values and values["forca"] == 0 and v == 0:
            raise ValueError("Item deve ter pelo menos um atributo maior que zero")
        return v

# HERDANDO DA CLASSE
class ItemMagicoCriar(ItemMagicoBase):
    pass


# HERDANDO DA CLASSE
class ItemMagicoResposta(ItemMagicoBase):
    id: int
    personagem_id: Optional[int] = None

    class Config:
        orm_mode = True


# CLASSE BASE PARA HERANÇA
class PersonagemBase(BaseModel):
    nome: str
    nome_aventureiro: str
    classe: ClassePersonagem
    level: conint(ge=1) = 1
    forca_base: conint(ge=0, le=10)
    defesa_base: conint(ge=0, le=10)

    @validator("defesa_base")
    def validar_total_pontos(cls, v, values):
        if "forca_base" in values and values["forca_base"] + v > 10:
            raise ValueError("A soma de força e defesa não pode exceder 10 pontos")
        return v


class PersonagemCriar(PersonagemBase):
    pass


class AtualizarNomeAventureiro(BaseModel):
    nome_aventureiro: str


class PersonagemResposta(PersonagemBase):
    id: int
    forca_total: int
    defesa_total: int
    itens_magicos: List[ItemMagicoResposta] = []

    class Config:
        orm_mode = True


class AdicionarItemPersonagem(BaseModel):
    item_id: int


## =============================== ##
## VALIDAÇÃO DE DADOS COM PYDANTIC ##
## =============================== ##


# =============================== #
# ROTAS API           #
# =============================== #

# =================== #
# Rotas de Personagem #
# =================== #


@app.post(
    "/personagens/",
    response_model=PersonagemResposta,
    tags=["Personagens"],
    summary="Cadastrar Personagem",
)
async def criar_personagem(personagem: PersonagemCriar, db: Session = Depends(get_db)):
    """
    Cria um novo personagem no sistema.
    """
    db_personagem = Personagem(
        nome=personagem.nome,
        nome_aventureiro=personagem.nome_aventureiro,
        classe=personagem.classe,
        level=personagem.level,
        forca_base=personagem.forca_base,
        defesa_base=personagem.defesa_base,
    )
    db.add(db_personagem)
    db.commit()
    db.refresh(db_personagem)
    return db_personagem


@app.get(
    "/personagens/",
    response_model=List[PersonagemResposta],
    tags=["Personagens"],
    summary="Listar Personagens",
)
async def listar_personagens(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Lista todos os personagens cadastrados no sistema.
    """
    personagens = db.query(Personagem).offset(skip).limit(limit).all()
    return personagens


@app.get(
    "/personagens/{personagem_id}",
    response_model=PersonagemResposta,
    tags=["Personagens"],
    summary="Buscar Personagem por Identificador",
)
async def buscar_personagem(
    personagem_id: int = Path(..., title="ID do Personagem"),
    db: Session = Depends(get_db),
):
    """
    Busca um personagem pelo seu identificador único.
    """
    personagem = db.query(Personagem).filter(Personagem.id == personagem_id).first()
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")
    return personagem


@app.put(
    "/personagens/{personagem_id}/nome-aventureiro",
    response_model=PersonagemResposta,
    tags=["Personagens"],
    summary="Atualizar Nome de Aventureiro por Identificador",
)
async def atualizar_nome_aventureiro(
    personagem_id: int = Path(..., title="ID do Personagem"),
    dados: AtualizarNomeAventureiro = None,
    db: Session = Depends(get_db),
):
    """
    Atualiza o nome de aventureiro de um personagem existente.
    """
    personagem = db.query(Personagem).filter(Personagem.id == personagem_id).first()
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")

    personagem.nome_aventureiro = dados.nome_aventureiro
    db.commit()
    db.refresh(personagem)
    return personagem


@app.delete(
    "/personagens/{personagem_id}",
    response_model=dict,
    tags=["Personagens"],
    summary="Remover Personagem",
)
async def remover_personagem(
    personagem_id: int = Path(..., title="ID do Personagem"),
    db: Session = Depends(get_db),
):
    """
    Remove um personagem do sistema.
    """
    personagem = db.query(Personagem).filter(Personagem.id == personagem_id).first()
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")

    for item in personagem.itens_magicos:
        item.personagem_id = None

    db.delete(personagem)
    db.commit()
    return {"mensagem": f"Personagem {personagem_id} removido com sucesso"}


## =================== ##
## Rotas de Personagem ##
## =================== ##


# ==================== #
# Rotas de Item Mágico #
# ==================== #


@app.post(
    "/itens-magicos/",
    response_model=ItemMagicoResposta,
    tags=["Itens Mágicos"],
    summary="Cadastrar Item Mágico",
)
async def criar_item_magico(item: ItemMagicoCriar, db: Session = Depends(get_db)):
    """
    Cria um novo item mágico no sistema.
    """
    db_item = ItemMagico(
        nome=item.nome, tipo=item.tipo, forca=item.forca, defesa=item.defesa
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get(
    "/itens-magicos/",
    response_model=List[ItemMagicoResposta],
    tags=["Itens Mágicos"],
    summary="Listar Itens Mágicos",
)
async def listar_itens_magicos(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """
    Lista todos os itens mágicos cadastrados no sistema.
    """
    itens = db.query(ItemMagico).offset(skip).limit(limit).all()
    return itens


@app.get(
    "/itens-magicos/{item_id}",
    response_model=ItemMagicoResposta,
    tags=["Itens Mágicos"],
    summary="Buscar Item Mágico por Identificador",
)
async def buscar_item_magico(
    item_id: int = Path(..., title="ID do Item Mágico"), db: Session = Depends(get_db)
):
    """
    Busca um item mágico pelo seu identificador único.
    """
    item = db.query(ItemMagico).filter(ItemMagico.id == item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item mágico não encontrado")
    return item


@app.post(
    "/personagens/{personagem_id}/adicionar-item",
    response_model=PersonagemResposta,
    tags=["Itens Mágicos e Personagens"],
    summary="Adicionar Item Mágico ao Personagem",
)
async def adicionar_item_personagem(
    personagem_id: int = Path(..., title="ID do Personagem"),
    dados: AdicionarItemPersonagem = None,
    db: Session = Depends(get_db),
):
    """
    Adiciona um item mágico existente a um personagem.
    """
    personagem = db.query(Personagem).filter(Personagem.id == personagem_id).first()
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")

    item = db.query(ItemMagico).filter(ItemMagico.id == dados.item_id).first()
    if item is None:
        raise HTTPException(status_code=404, detail="Item mágico não encontrado")

    if item.personagem_id is not None and item.personagem_id != personagem_id:
        raise HTTPException(
            status_code=400, detail="Item já atribuído a outro personagem"
        )

    if item.tipo == TipoItem.AMULETO:
        amuleto_existente = (
            db.query(ItemMagico)
            .filter(
                ItemMagico.personagem_id == personagem_id,
                ItemMagico.tipo == TipoItem.AMULETO,
            )
            .first()
        )

        if amuleto_existente and amuleto_existente.id != item.id:
            raise HTTPException(
                status_code=400,
                detail="Personagem já possui um amuleto. Remova o amuleto atual antes de adicionar outro.",
            )

    item.personagem_id = personagem.id
    db.commit()
    db.refresh(personagem)

    return personagem


@app.get(
    "/personagens/{personagem_id}/itens",
    response_model=List[ItemMagicoResposta],
    tags=["Itens Mágicos e Personagens"],
    summary="Listar Itens Mágicos por Personagem",
)
async def listar_itens_por_personagem(
    personagem_id: int = Path(..., title="ID do Personagem"),
    db: Session = Depends(get_db),
):
    """
    Lista todos os itens mágicos que pertencem a um personagem específico.
    """
    personagem = db.query(Personagem).filter(Personagem.id == personagem_id).first()
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")

    return personagem.itens_magicos


@app.delete(
    "/personagens/{personagem_id}/itens/{item_id}",
    response_model=dict,
    tags=["Itens Mágicos e Personagens"],
    summary="Remover Item Mágico do Personagem",
)
async def remover_item_do_personagem(
    personagem_id: int = Path(..., title="ID do Personagem"),
    item_id: int = Path(..., title="ID do Item Mágico"),
    db: Session = Depends(get_db),
):
    """
    Remove um item mágico de um personagem (não exclui o item do sistema).
    """
    personagem = db.query(Personagem).filter(Personagem.id == personagem_id).first()
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")

    item = (
        db.query(ItemMagico)
        .filter(ItemMagico.id == item_id, ItemMagico.personagem_id == personagem_id)
        .first()
    )

    if item is None:
        raise HTTPException(
            status_code=404, detail="Item não encontrado no inventário deste personagem"
        )

    item.personagem_id = None
    db.commit()

    return {"mensagem": f"Item {item_id} removido do personagem {personagem_id}"}


@app.get(
    "/personagens/{personagem_id}/amuleto",
    response_model=ItemMagicoResposta,
    tags=["Itens Mágicos e Personagens"],
    summary="Buscar Amuleto do Personagem",
)
async def buscar_amuleto_personagem(
    personagem_id: int = Path(..., title="ID do Personagem"),
    db: Session = Depends(get_db),
):
    """
    Busca o amuleto de um personagem específico.
    """
    personagem = db.query(Personagem).filter(Personagem.id == personagem_id).first()
    if personagem is None:
        raise HTTPException(status_code=404, detail="Personagem não encontrado")

    amuleto = (
        db.query(ItemMagico)
        .filter(
            ItemMagico.personagem_id == personagem_id,
            ItemMagico.tipo == TipoItem.AMULETO,
        )
        .first()
    )

    if amuleto is None:
        raise HTTPException(status_code=404, detail="Personagem não possui amuleto")

    return amuleto


## ==================== ##
## Rotas de Item Mágico ##
## ==================== ##

## =============================== ##
##            ROTAS API            ##
## =============================== ##
