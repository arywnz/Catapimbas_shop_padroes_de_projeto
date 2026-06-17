import unittest
import json
import os
import sys


sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, Pedido, FabricaEntrega, repositorio_pedido, db

class TestOrderService(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def test_alteracao_status_pedido(self):
        
        pedido = Pedido(produto="Teclado Gamer", valor=299.90)
        self.assertEqual(pedido.status, "AGUARDANDO_PAGAMENTO")
        
        pedido.alterar_status("PAGAMENTO_APROVADO")
        self.assertEqual(pedido.status, "PAGAMENTO_APROVADO")

    def test_metodo_fabrica_frete(self):
        
        pac = FabricaEntrega.criar("correios")
        self.assertEqual(pac.nome(), "Correios (PAC)")
        self.assertEqual(pac.calcular_frete("12345-678"), 25.90)

        express = FabricaEntrega.criar("transportadora")
        self.assertEqual(express.nome(), "Transportadora Expressa")
        
        with self.assertRaises(ValueError):
            FabricaEntrega.criar("invalido")

    def test_api_finalizar_compra_e_listar(self):
        
        payload = {
            'nomeCliente': 'João Silva',
            'produto': 'Mouse Gamer',
            'valor': 150.00,
            'metodoPagamento': 'Pix',
            'tipoEntrega': 'transportadora',
            'cep': '24000-000',
            'email': 'teste@email.com'
        }
        
        
        res = self.client.post('/finalizar-compra', 
                              data=json.dumps(payload),
                              content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        self.assertIn('idPedido', data)
        self.assertEqual(data['status'], 'PAGAMENTO_APROVADO')
        
        
        res_list = self.client.get('/pedidos')
        self.assertEqual(res_list.status_code, 200)
        pedidos = json.loads(res_list.data)
        self.assertEqual(len(pedidos), 1)
        self.assertEqual(pedidos[0]['produto'], 'Mouse Gamer')

if __name__ == '__main__':
    unittest.main()
