# Luxus Brechó — Mobile

App React Native + **Expo 49** com TypeScript e NativeWind.

> Documentação completa do estado do app (incluindo os gaps com o backend): [docs/apps/mobile.md](../docs/apps/mobile.md). Divergências conhecidas: [docs/alinhamento-e-debitos.md](../docs/alinhamento-e-debitos.md#débitos-do-mobile).

## 🚀 Início Rápido

```bash
npm install
cp .env.example .env
npx expo start --clear
```

## ⚙️ Configuração (.env)

```env
EXPO_PUBLIC_API_URL=http://SEU_IP:5000/api
EXPO_PUBLIC_ENABLE_LOGS=true
```

> Execute `npm run dev` na raiz do projeto para sincronizar o IP automaticamente (gera `mobile/network-config.json`, lido em dev).

## 📂 Estrutura

```
├── app/          # Screens (Expo Router)
├── components/   # UI, Forms, Ecommerce
├── services/     # API, Auth
├── store/        # Zustand (auth, cart, favorites)
├── schemas/      # Validações Zod
└── types/        # TypeScript types
```

## 🔑 Funcionalidades

- **Catálogo** com filtros e busca (cache local de GETs via AsyncStorage)
- **Carrinho** com persistência local
- **Painel Admin** (role-based)

⚠️ **Estado real da autenticação:** o app **ainda não implementa JWT** — o login grava apenas uma flag no AsyncStorage. Por isso, os fluxos que exigem token no backend atual (favoritos, exclusão de conta, carrinho/pedidos no servidor) **não funcionam** contra a API. Detalhes: [docs/apps/mobile.md](../docs/apps/mobile.md#autenticação--estado-real).

## 📱 Executar

| Comando | Plataforma |
|---------|------------|
| `npx expo start` | QR Code (Expo Go) |
| `npm run android` | Android |
| `npm run ios` | iOS |
| `npm run web` | Web |

## 🧪 Testes

O Jest está configurado (`jest.config.js`), mas **ainda não há suítes de teste** — `npm test` não exercita nada.

## 📦 Stack

**Expo 49** · **TypeScript** · **Expo Router** · **Zustand** · **Zod** · **NativeWind**
