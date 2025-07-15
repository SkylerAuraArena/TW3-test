import { useState } from "react";
import { Geist, Geist_Mono } from "next/font/google";
import Header from "../components/header/Header";
import Chat from "../components/chat/chat";
import Footer from "../components/footer/Footer";
import { v4 as uuid } from "uuid";

/* -------------------- fonts -------------------- */
const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

/* -------------------- types -------------------- */
type Message = {
  id: string;
  date: Date | null;
  message: string;
  senderId: string;
  senderEmail: string;
};
const dummyUser = { uid: "u-tester", email: "tester@acme.io" };

/* -------------------- helpers ------------------ */
const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/* -------------------- page --------------------- */
export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [convId, setConvId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  /** Ajoute le message d’un rôle (user ou bot) dans la liste */
  const push = (content: string, sender: "user" | "bot") =>
    setMessages((prev) => [
      ...prev,
      {
        id: uuid(),
        date: new Date(),
        message: content,
        senderId: sender === "user" ? dummyUser.uid : "bot",
        senderEmail: sender === "user" ? dummyUser.email : "bot@tw3",
      },
    ]);

  const handleSend = async (text: string) => {
    // 1) affiche tout de suite le message de l’utilisateur
    push(text, "user");
    setIsLoading(true);
    // 2) requête POST   { question: "…" }
    try {
      const res = await fetch(`${API}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, conv_id: convId }),
      });
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();

      /* stocke le conv_id reçu au 1er tour */
      if (!convId) setConvId(data.conv_id);

      // 3) ajoute la réponse du bot
      push(data.answer, "bot");
    } catch (err) {
      push("❌ Erreur de connexion au serveur", "bot");
      /* eslint-disable no-console */
      console.error("API /ask error:", err);
      } finally {
        setIsLoading(false);
      }
  };

  return (
    <div className={`${geistSans.className} ${geistMono.className} w-full h-screen flex justify-items-start items-center flex-col bg-white bg-tw3-gradient font-[family-name:var(--font-geist-sans)]`}>
      <Header />
      <main className="flex items-center flex-col w-full h-screen pb-1">
        <Chat messages={messages} user={dummyUser} onSend={handleSend} isLoading={isLoading} />
      </main>
      <Footer />
    </div>
  );
}