# 🔄 Migração de Sessões do Telethon

## Problema

Sessões criadas com versões antigas do Telethon apresentam o erro:
```
table update_state has 6 columns but 5 values were supplied
```

Isso acontece porque a estrutura do banco SQLite mudou entre versões.

## Solução Automática (Recomendado)

### Pelo Sistema Web

1. Acesse a aba **Sessões**
2. Clique no botão **"Migrar Sessões"** (azul, ícone de chave inglesa)
3. Confirme a migração
4. Aguarde o processo completar
5. Depois clique em **"Validar Todas"** para verificar as sessões

### O que acontece:

- ✅ Backup automático de cada sessão antes da migração
- ✅ Atualiza a tabela `update_state` de 5 para 6 colunas
- ✅ Adiciona a coluna `unread_count` com valor padrão 0
- ✅ Preserva todos os dados de autenticação
- ✅ Remove o backup se a migração for bem-sucedida
- ✅ Restaura o backup se houver erro

## Solução Manual (Linha de Comando)

Se preferir migrar via terminal:

```bash
cd web_app
py migrate_sessions.py "C:\caminho\para\pasta\de\sessoes"
```

Exemplo:
```bash
py migrate_sessions.py "C:\Users\itach\AppData\Local\TelegramAutomation\sessions"
```

## Resultado Esperado

Após a migração, você verá:

```
✅ Migração completa!
   Total: 105 sessões
   🔄 Migradas: 104
   ✅ Já corretas: 1
   ❌ Falhas: 0
```

## Validação Automática

O sistema também tenta migrar automaticamente durante a validação:

1. Quando você clica em **"Validar Todas"**
2. Se uma sessão apresentar erro de SQLite
3. O sistema tenta migrar automaticamente
4. Se a migração funcionar, a sessão é validada
5. Se falhar, marca como corrompida

## Segurança

- ✅ Backup automático antes de qualquer modificação
- ✅ Rollback automático em caso de erro
- ✅ Não modifica dados de autenticação
- ✅ Apenas atualiza estrutura do banco

## Quando NÃO funciona

A migração pode falhar se:

- ❌ Arquivo de sessão está corrompido (não é SQLite válido)
- ❌ Arquivo está em uso por outro processo
- ❌ Sem permissão de escrita na pasta
- ❌ Disco cheio

Nestes casos, você precisará recriar a sessão usando o sistema de criação.

## Fluxo Recomendado

1. **Escanear Pasta** - Importa sessões que estão na pasta mas não no sistema
2. **Migrar Sessões** - Atualiza formato SQLite de todas as sessões
3. **Validar Todas** - Verifica quais sessões estão autorizadas

## Suporte

Se encontrar problemas:

1. Verifique os logs do servidor
2. Tente migrar uma sessão por vez usando a linha de comando
3. Se persistir, recrie a sessão usando o sistema de criação
