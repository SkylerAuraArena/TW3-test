import { Geist, Geist_Mono } from "next/font/google";
import Header from "../components/header/Header";
import Chat from "../components/chat/chat";
import { MOCK_MESSAGES } from "@/assets/data";
import Footer from "../components/footer/Footer";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const dummyUser = { uid: 'u-tester', email: 'tester@acme.io' };

export default function Home() {
  return (
    <div className={`${geistSans.className} ${geistMono.className} w-full h-screen flex justify-items-start items-center flex-col bg-white tems-center font-[family-name:var(--font-geist-sans)]`}>
      <Header />
      <main className="flex items-center flex-col w-full h-[90%] bg-tw3-gradient">
        <Chat messages={MOCK_MESSAGES} user={dummyUser} onSend={(txt) => console.log('send:', txt)} />;
      </main>
      <Footer />
    </div>
  );
}
