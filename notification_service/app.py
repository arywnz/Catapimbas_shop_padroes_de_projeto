import os
import json
import base64
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# =============================================================================
# PADRÃO 1: SINGLETON — Gerenciador de Logs de Notificações
# =============================================================================

class GerenciadorLog:
    _instancia = None

    def __new__(cls):
        if cls._instancia is None:
            cls._instancia = super().__new__(cls)
            cls._instancia._logs = []
            print("[SINGLETON] GerenciadorLog inicializado.")
        return cls._instancia

    def registrar(self, mensagem: str) -> None:
        entrada = f"[{datetime.now().strftime('%H:%M:%S')}] {mensagem}"
        self._logs.append(entrada)
        print(f"LOG >> {entrada}")

    def obter_todos(self):
        return self._logs

# =============================================================================
# PADRÃO 2 & 3: STRATEGY & FACTORY METHOD — Envio do email
# =============================================================================

class EstrategiaNotificacao(ABC):
    @abstractmethod
    def enviar(self, destinatario: str, mensagem: str) -> bool:
        pass

# Envio REAL de E-mail via SMTP (smtplib nativo do Python)
class EstrategiaNotificacaoEmail(EstrategiaNotificacao):
    def enviar(self, destinatario: str, mensagem: str) -> bool:
        log = GerenciadorLog()
        
        # Higienizar chaves
        env_clean = {k.strip(): v for k, v in os.environ.items()}
        smtp_server = env_clean.get("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(env_clean.get("SMTP_PORT", 587))
        smtp_user = env_clean.get("SMTP_USER")
        smtp_password = env_clean.get("SMTP_PASSWORD")

        if smtp_password:
            smtp_password = smtp_password.replace(" ", "")

        # Fallback para modo simulado caso credenciais SMTP estejam pendentes
        if not smtp_user or not smtp_password or smtp_user.strip() == "" or smtp_user == "seu-email@gmail.com":
            mensagem_limpa = mensagem.split(" | Nome:")[0] if " | Nome:" in mensagem else mensagem
            log.registrar(f"[SIMULADO] E-mail preparado para {destinatario} — Conteúdo: '{mensagem_limpa}' (Credenciais SMTP ausentes no .env)")
            return True

        try:
            id_pedido = "PEDIDO"
            status = "ATUALIZADO"
            nome_cliente = "Cliente"
            if '#' in mensagem:
                parts = mensagem.split('#')
                if len(parts) > 1:
                    id_pedido = parts[1].split(' ')[0]
            if "status: '" in mensagem:
                status = mensagem.split("status: '")[1].split("'")[0]
            if " | Nome: " in mensagem:
                nome_cliente = mensagem.split(" | Nome: ")[-1].strip()

            primeiro_nome = nome_cliente.split()[0].capitalize() if nome_cliente else "Cliente"

            status_labels = {
                'AGUARDANDO_PAGAMENTO': 'Aguardando Pagamento ⏳',
                'PAGAMENTO_APROVADO': 'Pagamento Aprovado ✅',
                'EM_SEPARACAO': 'Em Separação 📦',
                'ENVIADO': 'Enviado para Transporte 🚚',
                'ENTREGUE': 'Pedido Entregue 🎉'
            }
            status_label = status_labels.get(status, status.replace('_', ' '))

            steps = [
                ('AGUARDANDO_PAGAMENTO', 'Aguardando Pagamento'),
                ('PAGAMENTO_APROVADO', 'Pagamento Aprovado'),
                ('EM_SEPARACAO', 'Em Separação'),
                ('ENVIADO', 'Enviado'),
                ('ENTREGUE', 'Entregue')
            ]
            
            current_idx = 0
            for i, (key, _) in enumerate(steps):
                if key == status:
                    current_idx = i
                    break
            
            timeline_html = ""
            for i, (key, label) in enumerate(steps):
                if i < current_idx:
                    icon = "✅"
                    label_style = "color: #10b981; font-weight: 600;"
                elif i == current_idx:
                    icon = "🔵"
                    label_style = "color: #2563eb; font-weight: 700;"
                else:
                    icon = "⚪"
                    label_style = "color: #94a3b8;"
                    
                timeline_html += f"""
                <tr>
                  <td width="30" align="center" style="font-size: 16px; padding: 6px 0;">{icon}</td>
                  <td style="font-size: 14px; {label_style} padding: 6px 0;">{label}</td>
                </tr>
                """

            # Template do email enviado
            html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Atualização de Pedido - Catapimbas Shop</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
  <table width="100%" border="0" cellspacing="0" cellpadding="0" style="background-color: #f3f4f6; padding: 30px 10px;">
    <tr>
      <td align="center">
        <table width="600" border="0" cellspacing="0" cellpadding="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); border: 1px solid #e5e7eb;">
          
          <!-- HEADER -->
          <tr>
            <td align="center" style="background-color: #0c0d0f; padding: 30px 20px;">
              <span style="font-size: 24px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">Catapimbas <span style="color: #2563eb;">Shop</span></span>
              <div style="font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 5px;">Notificação de Pedido</div>
            </td>
          </tr>
          
          <!-- MAIN CONTENT -->
          <tr>
            <td style="padding: 40px 35px; color: #1f2937;">
              <h2 style="font-size: 20px; font-weight: 700; margin-top: 0; margin-bottom: 10px; color: #111827;">Olá, {primeiro_nome}!</h2>
              <p style="font-size: 15px; line-height: 1.6; color: #4b5563; margin-bottom: 25px;">
                Temos novidades sobre o seu pedido! O status da sua compra foi atualizado.
              </p>
              
              <!-- ORDER BANNER -->
              <table width="100%" border="0" cellspacing="0" cellpadding="15" style="background-color: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 30px;">
                <tr>
                  <td>
                    <div style="font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Código do Pedido</div>
                    <div style="font-size: 18px; font-weight: 700; color: #2563eb; margin: 4px 0 10px 0;">#{id_pedido}</div>
                    
                    <div style="font-size: 12px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px;">Status Atual</div>
                    <div style="font-size: 16px; font-weight: 700; color: #0f172a; margin-top: 4px;">{status_label}</div>
                  </td>
                </tr>
              </table>
              
              <!-- TIMELINE STEPS -->
              <h3 style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; margin-bottom: 15px;">Acompanhamento do Pedido</h3>
              <table width="100%" border="0" cellspacing="0" cellpadding="5" style="margin-bottom: 35px;">
                {timeline_html}
              </table>
              
              <!-- PRODUCT SUMMARY -->
              <h3 style="font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; color: #475569; margin-bottom: 15px;">Detalhes da Compra</h3>
              <table width="100%" border="0" cellspacing="0" cellpadding="10" style="border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;">
                <tr style="background-color: #f8fafc;">
                  <th align="left" style="font-size: 12px; font-weight: 700; color: #475569; border-bottom: 1px solid #e2e8f0;">Produto</th>
                  <th align="right" style="font-size: 12px; font-weight: 700; color: #475569; border-bottom: 1px solid #e2e8f0;">Valor</th>
                </tr>
                <tr>
                  <td style="font-size: 14px; color: #1e293b; border-bottom: 1px solid #e2e8f0;">Notebook Acer Predator</td>
                  <td align="right" style="font-size: 14px; font-weight: 700; color: #1e293b; border-bottom: 1px solid #e2e8f0;">R$ 8.999,90</td>
                </tr>
              </table>
              
              <p style="font-size: 13px; line-height: 1.5; color: #64748b; margin-top: 30px; margin-bottom: 0;">
                Se você tiver alguma dúvida sobre a sua entrega, por favor responda a este e-mail ou entre em contato com o nosso suporte.
              </p>
            </td>
          </tr>
          
          <!-- FOOTER -->
          <tr>
            <td align="center" style="background-color: #f8fafc; padding: 25px 20px; border-top: 1px solid #e2e8f0; color: #64748b; font-size: 12px;">
              <span style="font-weight: 600; color: #475569;">Catapimbas Shop</span>
              <span style="font-size: 11px; color: #94a3b8; display: inline-block; margin-top: 5px;">Este é um e-mail transacional automatizado.</span>
            </td>
          </tr>
          
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""

            msg = MIMEMultipart('alternative')
            msg['From'] = smtp_user
            msg['To'] = destinatario
            msg['Subject'] = f"Atualização do Pedido #{id_pedido} - Catapimbas Shop"
            
            msg.attach(MIMEText(mensagem, 'plain', 'utf-8'))
            msg.attach(MIMEText(html_content, 'html', 'utf-8'))

            server = smtplib.SMTP(smtp_server, smtp_port, timeout=5)
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, destinatario, msg.as_string())
            server.quit()

            log.registrar(f"[SUCESSO] E-mail de notificação enviado com sucesso para {destinatario}")
            return True
        except Exception as e:
            log.registrar(f"[ERRO] Falha ao enviar e-mail para {destinatario}: {e}")
            return False

# Factory Method de Notificações
class FabricaEstrategiaNotificacao:
    @staticmethod
    def criar(tipo_canal: str) -> EstrategiaNotificacao:
        canal = tipo_canal.lower()
        if canal == 'email':
            return EstrategiaNotificacaoEmail()
        else:
            raise ValueError(f"Canal de notificação desconhecido: {tipo_canal}")

# =============================================================================
# SERVIDOR FLASK (Infraestrutura / Rotas)
# =============================================================================

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get('PORT', 3002))

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'mensagem': 'API do Notification Service (Serviço de Notificações) está ativa!',
        'rotas_disponiveis': {
            '/saude': 'GET - Status do serviço',
            '/logs': 'GET - Obter logs estruturados das notificações',
            '/eventos': 'POST - Processar e enviar notificações'
        }
    }), 200

@app.route('/saude', methods=['GET'])
def saude():
    return jsonify({'status': 'UP', 'servico': 'notification-service'}), 200

@app.route('/logs', methods=['GET'])
def obter_logs():
    log = GerenciadorLog()
    logs_estruturados = []
    for entrada in log.obter_todos():
        parts = entrada.split("] ", 1)
        horario = parts[0][1:] if len(parts) > 1 else ""
        msg = parts[1] if len(parts) > 1 else entrada
        
        canal = 'sistema' if '[EVENTO]' in msg else 'email'

        # Formatar a mensagem do log para português
        mensagem_formatada = msg
        if "[SIMULADO]" in msg:
            mensagem_formatada = msg.replace("[SIMULADO]", "💡 [SIMULADO]")
        elif "[SUCESSO]" in msg:
            mensagem_formatada = msg.replace("[SUCESSO]", "✉️ [SUCESSO]")
        elif "[ERRO]" in msg:
            mensagem_formatada = msg.replace("[ERRO]", "❌ [ERRO]")
        elif "[EVENTO]" in msg:
            mensagem_formatada = msg.replace("[EVENTO]", "📥 [EVENTO]")
            
            status_translation = {
                'AGUARDANDO_PAGAMENTO': 'Aguardando Pagamento',
                'PAGAMENTO_APROVADO': 'Pagamento Aprovado',
                'EM_SEPARACAO': 'Em Separação',
                'ENVIADO': 'Enviado',
                'ENTREGUE': 'Entrega Concluída'
            }
            for k, v in status_translation.items():
                if k in mensagem_formatada:
                    mensagem_formatada = mensagem_formatada.replace(k, v)

        logs_estruturados.append({
            'horario': horario,
            'canal': canal,
            'destinatario': obter_destinatario_da_mensagem(msg),
            'mensagem': mensagem_formatada
        })
    return jsonify(logs_estruturados), 200

def obter_destinatario_da_mensagem(msg: str) -> str:
    if 'para ' in msg.lower():
        parts = msg.lower().split('para ', 1)[1].split(' ', 1)
        if parts and '@' in parts[0]:
            idx = msg.lower().find('para ') + 5
            return msg[idx:].split(' ')[0].strip("—'\"")
    if '[EVENTO]' in msg:
        return "Sistema"
    return "Cliente"

@app.route('/eventos', methods=['POST'])
def processar_evento():
    try:
        data = request.get_json()
        nome_evento = data.get('nomeEvento')
        dados = data.get('dados')

        if not nome_evento or not dados:
            return jsonify({'error': 'nomeEvento e dados são obrigatórios'}), 400

        id_pedido = dados.get('idPedido')
        status = dados.get('status')
        email = dados.get('emailCliente')
        nome_cliente = dados.get('nomeCliente', 'Cliente')

        msg = f"Seu pedido #{id_pedido} de e-commerce mudou para o status: '{status}'. | Nome: {nome_cliente}"

        log = GerenciadorLog()
        log.registrar(f"[EVENTO] Recebida alteração de status do Pedido #{id_pedido} para {status}")

        enviador_email = FabricaEstrategiaNotificacao.criar('email')
        sucesso_email = enviador_email.enviar(email, msg)

        return jsonify({
            'status': 'PROCESSADO',
            'emailEntregue': sucesso_email
        }), 200

    except Exception as e:
        print(f"[Event Handler Error] {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print(f"[NotificationService] Iniciando na porta {PORT}")
    app.run(host='0.0.0.0', port=PORT)
