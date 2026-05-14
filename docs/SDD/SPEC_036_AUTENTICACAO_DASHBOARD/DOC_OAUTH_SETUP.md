# OAuth Google Setup Guide

## Visão Geral

Este documento detalha como configurar o OAuth Google para o dashboard Phicube.

---

## Passo 1: Criar Projeto no Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um novo projeto ou selecione um existente
3. Nomeie o projeto (ex: `phicube-dashboard`)

---

## Passo 2: Configurar OAuth Consent

1. No menu lateral: **APIs e Serviços** → **Tela de consentimento OAuth**
2. Selecione **Externo** (para uso externo) ou **Interno** (para organização)
3. Preencha as informações:
   - **Nome do app**: Phicube Dashboard
   - **E-mail de suporte**: seu-email@gmail.com
   - **Domínios autorizados**: seu domínio de produção
4. Adicione **Escopos**:
   - `.../auth/userinfo.email` (ver email)
   - `.../auth/userinfo.profile` (ver perfil)
   - `openid` (autenticação OpenID)
5. Adicione **Usuários de teste** (opcional, para desenvolvimento)

---

## Passo 3: Criar Credenciais

1. No menu lateral: **APIs e Serviços** → **Credenciais**
2. Clique em **Criar Credenciais** → **ID do cliente OAuth**
3. Configure:
   - **Tipo de aplicação**: Aplicação web
   - **Nome**: Phicube Dashboard Web
4. **URIs de redirecionamento autorizados**:
   ```
   http://localhost:8080/auth/callback
   https://seudominio.com/auth/callback
   ```
5. Clique em **Criar**
6. **Importante**: Anote o `Client ID` e `Client Secret`

---

## Passo 4: Configurar Variáveis de Ambiente

No arquivo `.env`:

```bash
# OAuth Google (obrigatório)
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret-aqui
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback

# Segurança
AUTH_ALLOWED_EMAILS=seuemail@gmail.com,outro@email.com
AUTH_DEV_BYPASS=false

# Fallback para recovery (opcional)
AUTH_FALLBACK_USER=emergency
AUTH_FALLBACK_PASSWORD_HASH=$2b$12$...  # bcrypt hash

# JWT (gerar string segura)
JWT_SECRET=sua-chave-secreta-aqui-minimo-32-caracteres
```

### Gerar JWT Secret

```bash
# Python
python -c "import secrets; print(secrets.token_hex(32))"

# Linux/Mac
openssl rand -hex 32
```

### Gerar Fallback Password Hash

```bash
# Python
python -c "from passlib.context import CryptContext; pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto'); print(pwd_context.hash('sua-senha'))"
```

---

## Passo 5: Configuração por Ambiente

### Desenvolvimento Local

```bash
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback
AUTH_ALLOWED_EMAILS=seuemail@gmail.com
AUTH_DEV_BYPASS=true  # Permite login simples
JWT_SECRET=dev-secret-key
```

### Produção

```bash
GOOGLE_CLIENT_ID=seu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret
GOOGLE_REDIRECT_URI=https://seudominio.com/auth/callback
AUTH_ALLOWED_EMAILS=seuemail@gmail.com,outro@email.com
AUTH_DEV_BYPASS=false  # Obrigatório false em produção
JWT_SECRET=chave-segura-gerada
```

---

## Passo 6: Testar Configuração

### Verificar se OAuth está configurado

```bash
# Iniciar o dashboard
python -m src.api.main

# Verificar health
curl http://localhost:8080/health
```

### Testar Login

1. Acesse `http://localhost:8080`
2. Clique em "Login com Google"
3. Você será redirecionado para o Google
4. Após login, será redirecionado de volta com JWT

### Verificar Alertas

Se `AUTH_DEV_BYPASS=true` em produção, o health check retornará alerta:

```json
{
  "status": "healthy",
  "warnings": ["AUTH_DEV_BYPASS is enabled - not suitable for production"]
}
```

---

## Solução de Problemas

### "redirect_uri_mismatch"

- Verifique se o `GOOGLE_REDIRECT_URI` exatamente corresponde ao configurado no Google Console
- Lembre-se: `http://localhost:8080` ≠ `http://localhost:8080/`

### "access_denied"

- O email do usuário não está na lista `AUTH_ALLOWED_EMAILS`
- Adicione o email à lista ou remova a configuração

### "invalid_client"

- O `GOOGLE_CLIENT_SECRET` está incorreto
- Recupere no Google Console → Credenciais

---

## Segurança

### Nunca faça commit de secrets

O arquivo `.env` deve estar no `.gitignore`:

```gitignore
.env
.env.local
*.env
```

### Rotação de secrets

- Altere `JWT_SECRET` periodicamente (a cada 90 dias)
- Se `GOOGLE_CLIENT_SECRET` for comprometido, revogue no Google Console e crie novo

### Monitoramento

- Toda tentativa de login via fallback é logada na coleção `audit`
- Configure alertas para múltiplas tentativas falhas