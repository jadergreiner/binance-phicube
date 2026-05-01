# Contribuindo com o Binance Phicube

Obrigado por se interessar em contribuir com o **Binance Phicube**! 🎉

Este documento descreve as diretrizes para contribuir com o projeto de forma organizada e eficiente. Antes de começar, leia também o nosso [MANIFESTO.md](./MANIFESTO.md) para entender os princípios que guiam o projeto.

---

## 📋 Código de Conduta

Ao participar deste projeto, você concorda em respeitar o nosso [Código de Conduta](./CODE_OF_CONDUCT.md). Comportamentos desrespeitosos não serão tolerados.

---

## 🐛 Reportando Bugs

Se encontrou um bug, abra uma **Issue** no GitHub com as seguintes informações:

1. **Título claro** descrevendo o problema.
2. **Passos para reproduzir** o bug.
3. **Comportamento esperado** vs. **comportamento atual**.
4. **Ambiente**: sistema operacional, versão do Python, etc.
5. **Logs ou mensagens de erro** relevantes (nunca inclua credenciais ou chaves de API).

---

## 💡 Sugerindo Funcionalidades

Para sugerir uma nova funcionalidade:

1. Verifique se já existe uma Issue similar aberta.
2. Abra uma nova Issue com o label `enhancement`.
3. Descreva o problema que a funcionalidade resolve e como ela se alinha ao [MANIFESTO.md](./MANIFESTO.md).

---

## 🔧 Contribuindo com Código

### 1. Fork e Clone

```bash
# Faça um fork do repositório no GitHub e clone o seu fork
git clone https://github.com/<seu-usuario>/binance-phicube.git
cd binance-phicube
```

### 2. Crie uma Branch

Use nomes descritivos para suas branches:

```bash
git checkout -b feat/nome-da-funcionalidade
# ou
git checkout -b fix/descricao-do-bug
# ou
git checkout -b docs/atualizacao-de-documentacao
```

### 3. Faça suas Alterações

- Mantenha o código limpo e legível.
- Siga as convenções de estilo já existentes no projeto.
- **Nunca commite chaves de API, senhas ou qualquer credencial**.
- Adicione ou atualize testes para as funcionalidades que você alterar.

### 4. Commit com Mensagens Claras

Use mensagens de commit descritivas (em português ou inglês):

```
feat: adiciona monitoramento de múltiplos símbolos
fix: corrige cálculo do stop loss no Futures
docs: atualiza instruções de instalação no README
```

### 5. Abra um Pull Request

- Faça push da sua branch para o seu fork.
- Abra um Pull Request (PR) para a branch `main` deste repositório.
- Descreva claramente o que foi feito e referencie a Issue relacionada (ex.: `Closes #42`).
- Aguarde a revisão dos mantenedores.

---

## 🔒 Segurança

Se você descobrir uma vulnerabilidade de segurança, **não abra uma Issue pública**. Entre em contato diretamente com os mantenedores do projeto.

---

## 📌 Boas Práticas

- Toda contribuição deve estar alinhada aos princípios do [MANIFESTO.md](./MANIFESTO.md).
- Prefira pequenos PRs focados a grandes PRs com múltiplas mudanças.
- Documente o que você faz — código bem documentado facilita a manutenção.

---

Agradecemos sua contribuição! Juntos tornamos o **Binance Phicube** mais robusto e confiável. 🚀
