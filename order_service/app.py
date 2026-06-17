import os
import json
import uuid
import urllib.request
from abc import ABC, abstractmethod
from typing import List, Dict
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy

# =============================================================================
# DOMÍNIO E CONTRATOS (Domain & Interfaces)
# =============================================================================

class ObservadorPedido(ABC):
    @abstractmethod
    def atualizar(self, pedido_id: str, novo_status: str) -> None:
        pass

class Pedido:
    def __init__(self, produto: str, valor: float, nome_cliente: str = "", email: str = "", pedido_id: str = None, status: str = "AGUARDANDO_PAGAMENTO"):
        self.pedido_id = pedido_id or str(uuid.uuid4())[:8].upper()
        self.produto = produto
        self.valor = valor
        self.nome_cliente = nome_cliente
        self.email = email
        self.status = status
        self._observadores: List[ObservadorPedido] = []

    def adicionar_observador(self, obs: ObservadorPedido) -> None:
        self._observadores.append(obs)

    def remover_observador(self, obs: ObservadorPedido) -> None:
        self._observadores.remove(obs)

    def _notificar_observadores(self) -> None:
        for obs in self._observadores:
            obs.atualizar(self.pedido_id, self.status)

    def alterar_status(self, novo_status: str) -> None:
        self.status = novo_status
        self._notificar_observadores()

# Interface do Repositório (SOLID - DIP)
class IRepositorioPedido(ABC):
    @abstractmethod
    def salvar(self, pedido: Pedido) -> None:
        pass

    @abstractmethod
    def buscar_por_id(self, pedido_id: str) -> Pedido:
        pass

    @abstractmethod
    def buscar_todos(self) -> List[Pedido]:
        pass

# =============================================================================
# ADAPTADORES (Adapters)
# =============================================================================


class ObservadorPedidoHttp(ObservadorPedido):
    def __init__(self, url_servico_notificacao: str, nome_cliente: str, email_cliente: str):
        self.url_servico_notificacao = url_servico_notificacao
        self.nome_cliente = nome_cliente
        self.email = email_cliente

    def atualizar(self, pedido_id: str, novo_status: str) -> None:
        print(f"[Observador HTTP] Disparando webhook para status '{novo_status}' do pedido #{pedido_id}")
        dados = {
            'nomeEvento': 'AlteracaoStatusPedido',
            'dados': {
                'idPedido': pedido_id,
                'status': novo_status,
                'nomeCliente': self.nome_cliente,
                'emailCliente': self.email
            }
        }
        try:
            data = json.dumps(dados).encode('utf-8')
            req = urllib.request.Request(
                self.url_servico_notificacao,
                data=data,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=3) as res:
                if res.getcode() == 200:
                    print(f"[Observador HTTP] Evento entregue com sucesso.")
        except Exception as e:
            print(f"[Observador HTTP Error] Falha ao enviar evento: {e}")

db = SQLAlchemy()

class ModeloPedido(db.Model):
    __tablename__ = 'pedidos'
    pedido_id = db.Column(db.String(50), primary_key=True)
    produto = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)
    nome_cliente = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(150), nullable=True)


class RepositorioPedidoSql(IRepositorioPedido):
    def salvar(self, pedido: Pedido) -> None:
        modelo = ModeloPedido.query.filter_by(pedido_id=pedido.pedido_id).first()
        if not modelo:
            modelo = ModeloPedido(
                pedido_id=pedido.pedido_id,
                produto=pedido.produto,
                valor=pedido.valor,
                status=pedido.status,
                nome_cliente=pedido.nome_cliente,
                email=pedido.email
            )
            db.session.add(modelo)
        else:
            modelo.status = pedido.status
            modelo.nome_cliente = pedido.nome_cliente
            modelo.email = pedido.email
        db.session.commit()

    def buscar_por_id(self, pedido_id: str) -> Pedido:
        modelo = ModeloPedido.query.filter_by(pedido_id=pedido_id).first()
        if modelo:
            return Pedido(
                produto=modelo.produto,
                valor=modelo.valor,
                nome_cliente=modelo.nome_cliente or "",
                email=modelo.email or "",
                pedido_id=modelo.pedido_id,
                status=modelo.status
            )
        return None

    def buscar_todos(self) -> List[Pedido]:
        modelos = ModeloPedido.query.all()
        return [
            Pedido(
                produto=m.produto,
                valor=m.valor,
                nome_cliente=m.nome_cliente or "",
                email=m.email or "",
                pedido_id=m.pedido_id,
                status=m.status
            )
            for m in modelos
        ]

# =============================================================================
# PADRÕES DE PROJETO (Design Patterns: Facade & Factory Method)
# =============================================================================

class EntregaBase(ABC):
    @abstractmethod
    def calcular_frete(self, cep_destino: str) -> float: pass
    @abstractmethod
    def prazo_estimado(self) -> str: pass
    @abstractmethod
    def nome(self) -> str: pass

class EntregaCorreios(EntregaBase):
    def calcular_frete(self, cep_destino: str) -> float: return 25.90
    def prazo_estimado(self) -> str: return "5 a 8 dias úteis"
    def nome(self) -> str: return "Correios (PAC)"

class EntregaTransportadora(EntregaBase):
    def calcular_frete(self, cep_destino: str) -> float: return 18.50
    def prazo_estimado(self) -> str: return "2 a 4 dias úteis"
    def nome(self) -> str: return "Transportadora Expressa"

class RetiradaLoja(EntregaBase):
    def calcular_frete(self, cep_destino: str) -> float: return 0.00
    def prazo_estimado(self) -> str: return "Disponível em 1 dia útil"
    def nome(self) -> str: return "Retirada na Loja"

# Factory Method
class FabricaEntrega:
    @staticmethod
    def criar(tipo: str) -> EntregaBase:
        catalogo = {
            "correios": EntregaCorreios(),
            "transportadora": EntregaTransportadora(),
            "retirada": RetiradaLoja(),
        }
        if tipo not in catalogo:
            raise ValueError(f"Tipo de entrega desconhecido: '{tipo}'")
        return catalogo[tipo]

# Subsistemas da Facade
class SubsistemaEstoque:
    def verificar(self, produto: str) -> bool:
        return True

class SubsistemaPagamento:
    def validar(self, valor: float, metodo: str) -> bool:
        return True

# Facade
class FachadaCheckout:
    def __init__(self):
        self._estoque = SubsistemaEstoque()
        self._pagamento = SubsistemaPagamento()

    def realizar_checkout(self, pedido: Pedido, metodo_pagamento: str, tipo_entrega: str, cep: str) -> bool:
        if not self._estoque.verificar(pedido.produto):
            return False

        if not self._pagamento.validar(pedido.valor, metodo_pagamento):
            return False

        entrega = FabricaEntrega.criar(tipo_entrega)
        frete = entrega.calcular_frete(cep)

        pedido.alterar_status("PAGAMENTO_APROVADO")
        return True

# =============================================================================
# SERVIDOR FLASK (Infraestrutura / Rotas)
# =============================================================================

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 3001))
NOTIFICATION_SERVICE_URL = os.environ.get('NOTIFICATION_SERVICE_URL', 'http://localhost:3002/eventos')


from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

db_url = os.environ.get('DATABASE_URL', 'sqlite:///orders.db')
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

with app.app_context():
    db.create_all()

repositorio_pedido = RepositorioPedidoSql()
fachada_checkout = FachadaCheckout()

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'mensagem': 'API do Order Service (Serviço de Pedidos) está ativa!',
        'rotas_disponiveis': {
            '/saude': 'GET - Status do serviço',
            '/finalizar-compra': 'POST - Processar checkout',
            '/pedidos': 'GET - Listar todos os pedidos',
            '/pedidos/<id>/status': 'POST - Alterar status do pedido'
        }
    }), 200

@app.route('/saude', methods=['GET'])
def saude():
    return jsonify({'status': 'UP', 'servico': 'order-service'}), 200

@app.route('/finalizar-compra', methods=['POST'])
def finalizar_compra():
    try:
        data = request.get_json()
        nome_cliente = data.get('nomeCliente', 'Cliente')
        produto = data.get('product') or data.get('produto')
        valor = float(data.get('value') or data.get('valor') or 0)
        metodo_pagamento = data.get('paymentMethod') or data.get('metodoPagamento')
        tipo_entrega = data.get('deliveryType') or data.get('tipoEntrega')
        cep = data.get('cep')
        email = data.get('email')

        if not all([produto, valor, metodo_pagamento, tipo_entrega, cep, email]):
            return jsonify({'error': 'Todos os campos são obrigatórios'}), 400

        # Validação do formato de e-mail 
        import re
        email_regex = r'^[^@\s]+@[^@\s]+\.[^@\s]+$'
        if not email or not re.match(email_regex, email.strip()):
            return jsonify({'error': 'E-mail inválido! Verifique o formato digitado (exemplo: usuario@gmail.com)'}), 400

        pedido = Pedido(produto=produto, valor=valor, nome_cliente=nome_cliente, email=email)

        
        observador = ObservadorPedidoHttp(NOTIFICATION_SERVICE_URL, nome_cliente, email)
        pedido.adicionar_observador(observador)

        sucesso = fachada_checkout.realizar_checkout(pedido, metodo_pagamento, tipo_entrega, cep)

        if sucesso:
            repositorio_pedido.salvar(pedido)
            return jsonify({
                'idPedido': pedido.pedido_id,
                'produto': pedido.produto,
                'valor': pedido.valor,
                'status': pedido.status,
                'email': email
            }), 201
        else:
            return jsonify({'error': 'Falha no processamento de checkout'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pedidos', methods=['GET'])
def listar_pedidos():
    try:
        pedidos = repositorio_pedido.buscar_todos()
        return jsonify([
            {
                'idPedido': p.pedido_id,
                'produto': p.produto,
                'valor': p.valor,
                'status': p.status
            }
            for p in pedidos
        ]), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/pedidos/<id>/status', methods=['POST'])
def atualizar_status(id):
    try:
        data = request.get_json() or {}
        novo_status = data.get('status')
        email = data.get('email')

        if not novo_status:
            return jsonify({'error': 'Status é obrigatório'}), 400

        pedido = repositorio_pedido.buscar_por_id(id)
        if not pedido:
            return jsonify({'error': 'Pedido não encontrado'}), 404

        email_resolvido = email or pedido.email

        if email_resolvido:
            observador = ObservadorPedidoHttp(NOTIFICATION_SERVICE_URL, pedido.nome_cliente, email_resolvido)
            pedido.adicionar_observador(observador)

        pedido.alterar_status(novo_status)
        repositorio_pedido.salvar(pedido)

        return jsonify({'idPedido': pedido.pedido_id, 'status': pedido.status}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print(f"[OrderService] Iniciando na porta {PORT}")
    app.run(host='0.0.0.0', port=PORT)
