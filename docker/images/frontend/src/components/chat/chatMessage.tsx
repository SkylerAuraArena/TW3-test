import { memo, useState } from 'react';

/* ------------------------------------------------------------------ */
interface Message {
  date: Date | null;
  message: string;
  senderId: string;
  senderEmail: string;
}

interface Props {
  message: Message;
  currentUid: string;
}
/* ------------------------------------------------------------------ */

const ChatMessage: React.FC<Props> = ({ message, currentUid }) => {
  const [hover, setHover] = useState(false);

  const isMine   = currentUid === message.senderId;
  const trigram  = message.senderEmail.slice(0, 3).toUpperCase();
  const dateText = message.date
    ? message.date.toLocaleString()
    : 'Envoi en cours…';

  /* ---------- classes Tailwind dynamiques ---------- */
  const base   = `flex items-center gap-1 w-full text-white ${isMine ? 'justify-end' : ''}`;
  const bubble = `max-w-full break-words rounded-3xl px-3 py-3 leading-6 ${isMine ? 'modalChatColor-sent' : 'modalChatColor-received'}`;
  const avatar = `flex h-12 w-12 items-center justify-center rounded-full ${isMine ? 'modalChatColor-sent' : 'modalChatColor-received'}`;

  return (
    <div className={base} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>
      {!isMine && <p className={avatar}>{trigram}</p>}
      <span className={bubble}>
        {hover ? `Date : ${dateText}` : message.message}
      </span>
      {isMine && <p className={avatar}>{trigram}</p>}
    </div>
  );
};

export default memo(ChatMessage);