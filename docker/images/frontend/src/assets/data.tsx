/* ------------------------------------------------------------------
   Interface (rappel)
------------------------------------------------------------------ */
interface Message {
  id: string;
  date: Date | null;
  message: string;
  senderId: string;
  senderEmail: string;
}

/* ------------------------------------------------------------------
   Utilisateurs fictifs
------------------------------------------------------------------ */
const USERS = [
  { uid: 'u-alice',  email: 'alice@acme.io' },
  { uid: 'u-bob',    email: 'bob@acme.io'   },
  { uid: 'u-claire', email: 'claire@acme.io'},
  { uid: 'u-dan',    email: 'dan@acme.io'   },
];

/* ------------------------------------------------------------------
   Jeu de messages
------------------------------------------------------------------ */
export const MOCK_MESSAGES: Message[] = [
  {
    id: 'm-001',
    date: new Date('2025-07-13T09:00:10Z'),
    message: 'Hello tout le monde 👋',
    senderId: USERS[0].uid,
    senderEmail: USERS[0].email,
  },
  {
    id: 'm-002',
    date: new Date('2025-07-13T09:00:25Z'),
    message: 'Salut Alice ! Comment ça va ?',
    senderId: USERS[1].uid,
    senderEmail: USERS[1].email,
  },
  {
    id: 'm-003',
    date: new Date('2025-07-13T09:01:02Z'),
    message: 'Top, merci ! Vous avez vu le nouveau design du dashboard ?',
    senderId: USERS[0].uid,
    senderEmail: USERS[0].email,
  },
  {
    id: 'm-004',
    date: new Date('2025-07-13T09:02:15Z'),
    message: "Oui, j'adore le thème sombre 🌚",
    senderId: USERS[2].uid,
    senderEmail: USERS[2].email,
  },
  {
    id: 'm-005',
    date: new Date('2025-07-13T09:03:41Z'),
    message: 'Je viens de déployer la PR #42 en staging 🚀',
    senderId: USERS[1].uid,
    senderEmail: USERS[1].email,
  },
  {
    id: 'm-006',
    date: new Date('2025-07-13T09:04:03Z'),
    message: 'Super, je vais tester ça tout de suite.',
    senderId: USERS[3].uid,
    senderEmail: USERS[3].email,
  },
  {
    id: 'm-007',
    date: new Date('2025-07-13T09:05:12Z'),
    message: 'Les tests passent ✅',
    senderId: USERS[3].uid,
    senderEmail: USERS[3].email,
  },
  {
    id: 'm-008',
    date: new Date('2025-07-13T09:06:30Z'),
    message: 'On merge ? 😉',
    senderId: USERS[2].uid,
    senderEmail: USERS[2].email,
  },
  {
    id: 'm-009',
    date: new Date('2025-07-13T09:07:05Z'),
    message: 'Go ! 🎉',
    senderId: USERS[0].uid,
    senderEmail: USERS[0].email,
  },
  {
    id: 'm-010',
    date: new Date('2025-07-13T09:07:45Z'),
    message: "C'est parti pour la prod d'ici midi.",
    senderId: USERS[1].uid,
    senderEmail: USERS[1].email,
  },
];
