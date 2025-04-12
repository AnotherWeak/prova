from sqlalchemy import Column, Integer, String, ForeignKey, Enum, CheckConstraint
from database import Base
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum

class ClassePersonagem(str, PyEnum):
    GUERREIRO = "Guerreiro"
    MAGO = "Mago"
    ARQUEIRO = "Arqueiro"
    LADINO = "Ladino"
    BARDO = "Bardo"

class TipoItem(str, PyEnum):
    ARMA = "Arma"
    ARMADURA = "Armadura"
    AMULETO = "Amuleto"

# USO DE HERANÇA
class Personagem(Base):
    __tablename__ = "personagens"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    nome_aventureiro = Column(String, nullable=False)
    classe = Column(Enum(ClassePersonagem), nullable=False)
    level = Column(Integer, nullable=False, default=1)
    forca_base = Column(Integer, nullable=False)
    defesa_base = Column(Integer, nullable=False)
    
    itens_magicos = relationship("ItemMagico", back_populates="personagem", cascade="save-update")
    # Constraint para garantir que a soma de força e defesa base seja no máximo 10
    __table_args__ = (
        CheckConstraint('forca_base + defesa_base <= 10', name='check_pontos_totais'),
        CheckConstraint('forca_base >= 0', name='check_forca_positiva'),
        CheckConstraint('defesa_base >= 0', name='check_defesa_positiva'),
        {'extend_existing': True}
    )
    
    @property
    def forca_total(self):
        """Calcula a força total do personagem (base + itens)"""
        return self.forca_base + sum(item.forca for item in self.itens_magicos)
    
    @property
    def defesa_total(self):
        """Calcula a defesa total do personagem (base + itens)"""
        return self.defesa_base + sum(item.defesa for item in self.itens_magicos)
    
    @property
    def amuleto(self):
        """Retorna o amuleto do personagem, se houver"""
        amuletos = [item for item in self.itens_magicos if item.tipo == TipoItem.AMULETO]
        return amuletos[0] if amuletos else None

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "nome_aventureiro": self.nome_aventureiro,
            "classe": self.classe,
            "level": self.level,
            "forca": self.forca_total,
            "defesa": self.defesa_total,
            "itens_magicos": [item.to_dict() for item in self.itens_magicos]
        }

class ItemMagico(Base):
    __tablename__ = "itens_magicos"
    
    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(Enum(TipoItem), nullable=False)
    forca = Column(Integer, nullable=False, default=0)
    defesa = Column(Integer, nullable=False, default=0)
    personagem_id = Column(Integer, ForeignKey("personagens.id"), nullable=True)
    
    personagem = relationship("Personagem", back_populates="itens_magicos")
    
    # Constraints para garantir as regras de negócio
    __table_args__ = (
        # Garante que os valores de força e defesa sejam válidos
        CheckConstraint('forca >= 0 AND forca <= 10', name='check_forca_valida'),
        CheckConstraint('defesa >= 0 AND defesa <= 10', name='check_defesa_valida'),
        # Garante que pelo menos um dos atributos seja maior que zero
        CheckConstraint('forca > 0 OR defesa > 0', name='check_item_tem_atributo'),
        # Garante que armas tenham defesa zero
        CheckConstraint('(tipo != "Arma") OR (tipo = "Arma" AND defesa = 0)', name='check_arma_sem_defesa'),
        # Garante que armaduras tenham força zero
        CheckConstraint('(tipo != "Armadura") OR (tipo = "Armadura" AND forca = 0)', name='check_armadura_sem_forca'),
        {'extend_existing': True}
    )
    
    #POLIMORFISMO E ABSTRAÇÃO
    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "tipo": self.tipo,
            "forca": self.forca,
            "defesa": self.defesa
        }
