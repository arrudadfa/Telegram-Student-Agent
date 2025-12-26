"""
Configuração centralizada de produtos
Facilita a criação de novos produtos e alteração de preços
"""

from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class Product:
    """Classe para representar um produto"""
    id: str
    name: str
    product_type: str  # 'gpt_premium', 'redacao', 'cronograma', etc.
    price: float
    link: Optional[str] = None
    description: Optional[str] = None
    active: bool = True

# Lista de produtos disponíveis
PRODUCTS: Dict[str, Product] = {
    'gpt_premium': Product(
        id='gpt_premium',
        name='GPT Premium',
        product_type='gpt_premium',
        price=50.0,
        link='https://chatgpt.com/g/g-692ee46d0f408191b4382ee654a3197e-corretor-de-redacoes-e-plano-de-estudos',
        description='Acesso vitalício ao GPT Premium com correção de redações, ajuda com exercícios e cronograma de estudos',
        active=True
    ),
    # Adicione novos produtos aqui:
    # 'redacao_avulsa': Product(
    #     id='redacao_avulsa',
    #     name='Correção de Redação Avulsa',
    #     product_type='redacao',
    #     price=10.0,
    #     description='Correção individual de redação',
    #     active=True
    # ),
}

def get_product(product_id: str) -> Optional[Product]:
    """
    Retorna um produto pelo ID
    
    Args:
        product_id: ID do produto
        
    Returns:
        Product ou None se não encontrado
    """
    product = PRODUCTS.get(product_id)
    if product and product.active:
        return product
    return None

def get_product_by_type(product_type: str) -> Optional[Product]:
    """
    Retorna um produto pelo tipo
    
    Args:
        product_type: Tipo do produto
        
    Returns:
        Product ou None se não encontrado
    """
    for product in PRODUCTS.values():
        if product.product_type == product_type and product.active:
            return product
    return None

def get_all_active_products() -> Dict[str, Product]:
    """
    Retorna todos os produtos ativos
    
    Returns:
        Dicionário com produtos ativos
    """
    return {pid: p for pid, p in PRODUCTS.items() if p.active}

def add_product(product: Product) -> bool:
    """
    Adiciona um novo produto
    
    Args:
        product: Instância de Product
        
    Returns:
        True se adicionado com sucesso, False se já existe
    """
    if product.id in PRODUCTS:
        return False
    PRODUCTS[product.id] = product
    return True

def update_product_price(product_id: str, new_price: float) -> bool:
    """
    Atualiza o preço de um produto
    
    Args:
        product_id: ID do produto
        new_price: Novo preço
        
    Returns:
        True se atualizado, False se produto não encontrado
    """
    product = PRODUCTS.get(product_id)
    if product:
        product.price = new_price
        return True
    return False

def deactivate_product(product_id: str) -> bool:
    """
    Desativa um produto
    
    Args:
        product_id: ID do produto
        
    Returns:
        True se desativado, False se produto não encontrado
    """
    product = PRODUCTS.get(product_id)
    if product:
        product.active = False
        return True
    return False

