
# SRPG - Sistema de Registro de Ponto e Gestão

![GitHub repo size](https://img.shields.io/github/repo-size/enarciso2009/srpg?color=blue)
![GitHub last commit](https://img.shields.io/github/last-commit/enarciso2009/srpg?color=green)
![GitHub language count](https://img.shields.io/github/languages/count/enarciso2009/srpg)
![GitHub top language](https://img.shields.io/github/languages/top/enarciso2009/srpg)

Sistema de Registro e Gestão de Presenças (SRPG)  
Projeto **fullstack** com **Django** no backend e **React Native / Expo** no mobile.

---

## 🗂 Estrutura do projeto


<img width="361" height="116" alt="image" src="https://github.com/user-attachments/assets/226b68c0-9ec1-4613-be7b-210a5d1a5a4c" />

---

## 🚀 Tecnologias

### Backend
- Python 3.x
- Django Framework
- Django REST Framework
- SQLite (dev) / MySQL ou PostgreSQL (produção)

### Mobile
- React Native
- Expo
- TypeScript
- Context API (Auth)
- Axios para chamadas HTTP

---

## ⚡ Funcionalidades principais

- Autenticação de usuários
- Registro de presença (início/fim de turno)
- Acompanhamento funcionarios externos recebendo latitude e longitude
- API REST para integração mobile
- Controle de usuários e permissões

---

## 🛠 Setup e execução

### Backend
1. Acesse a pasta do backend:
cd backend

2. Crie e ative o virtualenv:
python -m venv venv
source venv/bin/activate

3. Instale as dependências:
   pip install -r requirements.txt

4.Rode as migrações:
  python manage.py migrate

5.Execute o servidor:
  python manage.py runserver 0.0.0.0:8000

### Mobile
1. Acesse a pasta do mobile:
  cd mobile

2. Instale as dependências:
   npm install
   ou
   yarn install

3. Rode o app com Expo:
   expo start
---
📌 Uso
  * Acesse a API no backend via http://127.0.0.1:8000
  * Use aplicativo Expo para testar o mobile
  * CRUD de contas, turnos e registros de ponto disponivel
---
🔐 Segurança 
 * Não versionar arquivos sensíveis ( .env, venv/, node_modules/ )
 * Usar tokens JWT para autenticação da API
---
**Desenvolvido por Everton Narciso & Lua (assistente AI)**  
---
