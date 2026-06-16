import unittest
import unittest.mock
import json
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import app, GerenciadorLog, FabricaEstrategiaNotificacao

class TestNotificationService(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # Resetar o Singleton do log
        GerenciadorLog()._logs.clear()

    def test_singleton_gerenciador_log(self):
        # Teste Unitário TDD verificando o padrão Singleton
        log1 = GerenciadorLog()
        log2 = GerenciadorLog()
        self.assertIs(log1, log2)

        log1.registrar("Log de teste")
        self.assertEqual(len(log2.obter_todos()), 1)

    def test_metodo_fabrica_estrategia(self):
        # Teste Unitário TDD para o Factory Method de estratégias de notificação
        email_strat = FabricaEstrategiaNotificacao.criar("email")
        self.assertEqual(email_strat.__class__.__name__, "EstrategiaNotificacaoEmail")

        with self.assertRaises(ValueError):
            FabricaEstrategiaNotificacao.criar("sms")

    @unittest.mock.patch('app.smtplib.SMTP')
    def test_api_processar_evento(self, mock_smtp):
        # Configurar mock do SMTP para simular envio real
        mock_smtp_instance = mock_smtp.return_value

        # Teste de Integração BDD
        evento = {
            'nomeEvento': 'AlteracaoStatusPedido',
            'dados': {
                'idPedido': '12345',
                'status': 'PAGAMENTO_APROVADO',
                'emailCliente': 'cliente@teste.com'
            }
        }
        res = self.client.post('/eventos', 
                              data=json.dumps(evento),
                              content_type='application/json')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data['status'], 'PROCESSADO')

if __name__ == '__main__':
    unittest.main()
