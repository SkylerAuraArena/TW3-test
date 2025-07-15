import React, { useState } from "react";
import Image from "next/image";

const NAV_ITEMS = [
  { label: "PRODUIT", href: "https://tw3partners.fr/fr/produit/" },
  { label: "SERVICES", href: "https://tw3partners.fr/fr/services/" },
  { label: "À PROPOS", href: "https://tw3partners.fr/fr/a-propos-de-nous/" },
  { label: "RAPPORTS", href: "https://tw3partners.fr/fr/accueil/" },
  { label: "BLOG", href: "https://tw3partners.fr/fr/accueil/" },
  { label: "CONTACT", href: "https://tw3partners.fr/fr/contact/" },
] as const;

const LANG_FLAGS = [
  { src: "/uk-flag.png", alt: "UK flag", href: "https://tw3partners.fr/" },
  { src: "/fr-flag.png", alt: "French flag", href: "https://tw3partners.fr/fr/accueil/" },
] as const;

const NavItem = ({ href, children }: { href: string; children: React.ReactNode }) => (
  <div className="hover-link cursor-pointer hidden lg:flex lg:items-center lg:justify-center">
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  </div>
);

// Menu desktop "Ressources" uniquement
const Resources = () => (
  <div className="relative hidden flex-col group hover-link cursor-pointer lg:flex lg:items-center lg:justify-center">
    <a href="#" className="flexJIC gap-2">
      <span>RESSOURCES</span>
      <svg viewBox="0 0 320 512" className="h-4 w-4 fill-white" aria-hidden>
        <path d="M31.3 192h257.3c17.8 0 26.7 21.5 14.1 34.1L174.1 354.8c-7.8 7.8-20.5 7.8-28.3 0L17.2 226.1C4.6 213.5 13.5 192 31.3 192z" />
      </svg>
    </a>
    <div className="absolute top-full left-0 pt-0.5 hidden w-40 flex-col bg-white text-sm font-bold text-[var(--tw3grey)] shadow group-hover:flex">
      {["Rapports", "Blog"].map((label) => (
        <a key={label} href="https://tw3partners.fr/fr/accueil/" target="_blank" rel="noopener noreferrer" className="p-4 text-left duration-500 hover:bg-[var(--tw3grey)] hover:text-white">
          {label}
        </a>
      ))}
    </div>
  </div>
);

// CATÉGORIES : menu mobile (visible < lg)
function CategoriesMenu() {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative flex lg:hidden">
      <button
        className="flex items-center gap-2 bg-[var(--tw3grey)] text-white font-bold px-4 py-2 rounded shadow"
        onClick={() => setOpen((v) => !v)}
      >
        CATÉGORIES
        <svg className="h-4 w-4 fill-white" viewBox="0 0 320 512" aria-hidden>
          <path d="M31.3 192h257.3c17.8 0 26.7 21.5 14.1 34.1L174.1 354.8c-7.8 7.8-20.5 7.8-28.3 0L17.2 226.1C4.6 213.5 13.5 192 31.3 192z" />
        </svg>
      </button>
      {open && (
        <div className="absolute top-full right-0 mt-2 w-56 flex flex-col bg-white text-[var(--tw3grey)] font-bold rounded shadow z-50">
          {NAV_ITEMS.map(({ label, href }) => (
            <a
              key={label}
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="p-4 border-b last:border-none hover:bg-[var(--tw3grey)] hover:text-white duration-300"
              onClick={() => setOpen(false)}
            >
              {label}
            </a>
          ))}
          {/* Langues */}
          <div className="flex gap-2 justify-center p-2 border-t bg-gray-50">
            {LANG_FLAGS.map(({ src, alt, href }) => (
              <a key={alt} href={href} target="_blank" rel="noopener noreferrer">
                <Image src={src} alt={alt} width={30} height={20} aria-hidden />
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function Header() {
  const mainDesktop = NAV_ITEMS.filter(i =>
    ["PRODUIT", "SERVICES", "À PROPOS"].includes(i.label)
  );
  const contact = NAV_ITEMS.find(i => i.label === "CONTACT")!;

  return (
    <header className="flexJIC w-full bg-[var(--background)]">
      <div className="flex w-full items-center justify-between">
        <a className="hover:underline hover:underline-offset-4" href="https://tw3partners.fr/fr/accueil/" target="_blank" rel="noopener noreferrer">
          <Image src="/logo.png" alt="Logo TW3 Partners" width={160} height={126} aria-hidden />
        </a>
        <nav className="flex justify-center items-center gap-6 mr-2 sm:mr-6 lg:w-2/3 md:text-md lg:text-xl text-white">
          <CategoriesMenu />
          {mainDesktop.map(({ label, href }) => (
            <NavItem key={label} href={href}>{label}</NavItem>
          ))}
          <Resources />
          <NavItem href={contact.href}>{contact.label}</NavItem>
          <div className="w-full hidden gap-4 lg:flex lg:items-center lg:justify-center">
            {LANG_FLAGS.map(({ src, alt, href }) => (
              <a key={alt} href={href} target="_blank" rel="noopener noreferrer">
                <Image src={src} alt={alt} width={30} height={20} aria-hidden />
              </a>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
}