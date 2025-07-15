import { memo, useEffect, useRef, useState, KeyboardEvent } from 'react';
import ChatMessage from './chatMessage';

/* ------------------------------------------------------------------
   Types
------------------------------------------------------------------ */
interface Message {
  id: string;               // clé unique (Date.now(), uuid, etc.)
  date: Date | null;        // null le temps de l’envoi si besoin
  message: string;
  senderId: string;
  senderEmail: string;
}

interface User {
  uid: string;
  email: string;
}

interface ChatProps {
  messages: Message[];
  user: User;
  onSend: (text: string) => void;
  isLoading: boolean;
}

/* ------------------------------------------------------------------
   Composant
------------------------------------------------------------------ */
const TypingLoader = () => (
  <div className="tw3-typing-loader">
    <span />
    <span />
    <span />
  </div>
);

const Chat: React.FC<ChatProps> = ({ messages, user, onSend, isLoading }) => {
  const [text, setText] = useState('');
  const inputRef  = useRef<HTMLTextAreaElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  /* Scroll automatique vers le dernier message */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  /* Envoi du message + reset */
  const handleSend = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setText('');
    inputRef.current?.focus();
  };

  /* Entrée (sans Shift) pour envoyer */
  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className='flex flex-col justify-around items-center w-11/12 h-[100%] pb-2 lg:pb-6'>
      {/* ---------- barre de titre ---------- */}
      <header className="flexJIC w-full py-2 mt-3">
        <h1 className="pb-6 text-5xl text-white text-center">TW3 Qwen Chatbot</h1>
      </header>

      {/* ---------- liste des messages ---------- */}
      <section className="flexJIC flex-col w-full gap-3 overflow-y-auto px-3">
        {messages.map(msg => (
          <ChatMessage key={msg.id} message={msg} currentUid={user.uid} />
        ))}
        <div ref={bottomRef} />
        {isLoading && (
          <div className="flex w-full justify-start mb-2">
            <TypingLoader />
          </div>
        )}
      </section>

      {/* ---------- zone de saisie ---------- */}
      <footer className="mt-auto flexJIC items-center w-full gap-2 px-2 pb-4">
        <textarea id="chat-input" ref={inputRef} value={text} placeholder="Votre message..." onChange={e => setText(e.target.value)} onKeyDown={handleKey} rows={2} className="bg-white w-11/12 resize-none px-8 pt-4 h-20 mb-1 max-h-28 m-0 text-left min-w-auto border rounded-4xl"/>
        <button onClick={handleSend} className="flex h-full w-12 items-center justify-center rounded-full border-2 bg-[color:var(--tw3blue)] text-xl cursor-pointer hover:bg-white"aria-label="Envoyer">
          🕊️
        </button>
      </footer>
    </div>
  );
};

export default memo(Chat);