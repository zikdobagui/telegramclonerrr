# 🌐 TELEGRAM AUTOMATION - WEB APP

## Instalação

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

## Executar Localmente

```bash
python app.py
```

Acesse: http://localhost:5000

## Login Padrão

- Usuário: `admin`
- Senha: `admin123`

## Deploy no Discloud

1. Faça upload de todos os arquivos desta pasta
2. O Discloud usará o `discloud.config` automaticamente

## Estrutura

- `app.py` - Aplicativo Flask principal
- `templates/` - Templates HTML
- `static/` - CSS, JS, imagens
- `discloud.config` - Configuração do Discloud
- Arquivos compartilhados (session_manager, extractor, etc.)
