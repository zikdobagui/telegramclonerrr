#!/bin/bash
# Script para forçar atualização de dependências no Discloud

echo "🔄 Forçando reinstalação de dependências..."
echo ""
echo "PASSOS:"
echo "1. Pare o app no Discloud"
echo "2. Execute: git add . && git commit -m 'force deps update' && git push"
echo "3. Inicie o app novamente no Discloud"
echo ""
echo "Isso vai forçar o Discloud a reinstalar todas as dependências,"
echo "incluindo o Telethon 1.37.0+ que corrige o erro TypeNotFoundError"
