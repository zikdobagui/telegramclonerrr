#!/bin/bash
# Script de instalação do Bot Update Server
# Para VPS: 135.148.144.90

echo "=========================================="
echo "🚀 INSTALAÇÃO DO BOT UPDATE SERVER"
echo "=========================================="
echo ""

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Verifica se está rodando como root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Por favor, execute como root (sudo)${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Executando como root${NC}"
echo ""

# Atualiza sistema
echo "📦 Atualizando sistema..."
apt update -qq
apt upgrade -y -qq

# Instala Python e pip
echo "🐍 Instalando Python..."
apt install -y python3 python3-pip -qq

# Instala dependências
echo "📚 Instalando dependências Python..."
pip3 install aiogram flask --quiet

# Cria diretório
echo "📁 Criando diretório..."
mkdir -p /root/update_server
cd /root/update_server

# Cria estrutura
mkdir -p updates
mkdir -p logs

# Solicita informações
echo ""
echo "=========================================="
echo "⚙️  CONFIGURAÇÃO"
echo "=========================================="
echo ""

read -p "🤖 Token do Bot (do @BotFather): " BOT_TOKEN
read -p "👤 Seu ID do Telegram: " ADMIN_ID
read -p "🌐 Porta HTTP [8080]: " HTTP_PORT
HTTP_PORT=${HTTP_PORT:-8080}

# Cria arquivo de configuração
cat > config.json <<EOF
{
  "bot_token": "$BOT_TOKEN",
  "admin_ids": [$ADMIN_ID],
  "http_port": $HTTP_PORT,
  "server_ip": "135.148.144.90"
}
EOF

echo ""
echo -e "${GREEN}✅ Configuração salva em config.json${NC}"

# Configura firewall
echo ""
echo "🔥 Configurando firewall..."
ufw allow $HTTP_PORT/tcp
ufw --force enable

echo -e "${GREEN}✅ Porta $HTTP_PORT liberada${NC}"

# Cria serviço systemd
echo ""
echo "⚙️  Criando serviço systemd..."

cat > /etc/systemd/system/update-server.service <<EOF
[Unit]
Description=Bot Update Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/update_server
ExecStart=/usr/bin/python3 /root/update_server/update_server_bot.py
Restart=always
RestartSec=10
StandardOutput=append:/root/update_server/logs/output.log
StandardError=append:/root/update_server/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

# Recarrega systemd
systemctl daemon-reload
systemctl enable update-server

echo -e "${GREEN}✅ Serviço criado e habilitado${NC}"

# Cria script de teste
cat > test_server.sh <<'EOF'
#!/bin/bash
echo "🧪 Testando servidor..."
echo ""
echo "1. Verificando versão:"
curl -s http://localhost:8080/version | python3 -m json.tool
echo ""
echo "2. Verificando stats:"
curl -s http://localhost:8080/stats | python3 -m json.tool
echo ""
echo "✅ Teste concluído!"
EOF

chmod +x test_server.sh

# Resumo
echo ""
echo "=========================================="
echo "✅ INSTALAÇÃO CONCLUÍDA!"
echo "=========================================="
echo ""
echo "📋 Informações:"
echo "   • Diretório: /root/update_server"
echo "   • Porta HTTP: $HTTP_PORT"
echo "   • Admin ID: $ADMIN_ID"
echo ""
echo "🚀 Próximos passos:"
echo ""
echo "1. Copie o arquivo update_server_bot.py para este diretório:"
echo "   scp update_server_bot.py root@135.148.144.90:/root/update_server/"
echo ""
echo "2. Inicie o serviço:"
echo "   systemctl start update-server"
echo ""
echo "3. Verifique o status:"
echo "   systemctl status update-server"
echo ""
echo "4. Veja os logs:"
echo "   journalctl -u update-server -f"
echo ""
echo "5. Teste o servidor:"
echo "   ./test_server.sh"
echo ""
echo "🌐 URLs:"
echo "   • http://135.148.144.90:$HTTP_PORT/version"
echo "   • http://135.148.144.90:$HTTP_PORT/download"
echo "   • http://135.148.144.90:$HTTP_PORT/stats"
echo ""
echo "=========================================="
echo "📱 Envie /start para o bot no Telegram!"
echo "=========================================="
