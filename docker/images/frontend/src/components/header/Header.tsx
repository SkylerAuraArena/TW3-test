import Image from "next/image";

const NAV_ITEMS = [
  { label: "PRODUIT", href: "https://tw3partners.fr/fr/produit/" },
  { label: "SERVICES", href: "https://tw3partners.fr/fr/services/" },
  { label: "A PROPOS", href: "https://tw3partners.fr/fr/a-propos-de-nous/" },
  { label: "CONTACT",  href: "https://tw3partners.fr/fr/contact/" },
] as const;

const LANG_FLAGS = [
  { src: "/uk-flag.png", alt: "UK flag", href: "https://tw3partners.fr/" },
  { src: "/fr-flag.png", alt: "French flag", href: "https://tw3partners.fr/fr/accueil/" },
] as const;

const NavItem = ({ href, children }: { href: string; children: React.ReactNode }) => (
  <div className="flexJIC hover-link cursor-pointer">
    <a href={href} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  </div>
);

const Resources = () => (
  <div className="relative flexJIC flex-col group hover-link cursor-pointer">
    <a href="https://tw3partners.fr/fr/accueil/" target="_blank" rel="noopener noreferrer" className="flexJIC gap-2">
      <span>RESSOURCES</span>
      <svg viewBox="0 0 320 512" className="h-4 w-4 fill-white" aria-hidden>
        <path d="M31.3 192h257.3c17.8 0 26.7 21.5 14.1 34.1L174.1 354.8c-7.8 7.8-20.5 7.8-28.3 0L17.2 226.1C4.6 213.5 13.5 192 31.3 192z" />
      </svg>
    </a>

    <div className="absolute top-full left-0 pt-0.5 hidden w-10/12 flex-col bg-white text-sm font-bold text-[var(--tw3grey)] shadow group-hover:flex">
      {["Rapports", "Blog"].map((label) => (
        <a key={label} href="https://tw3partners.fr/fr/accueil/" target="_blank" rel="noopener noreferrer" className="p-4 text-left duration-500 hover:bg-[var(--tw3grey)] hover:text-white">
          {label}
        </a>
      ))}
    </div>
  </div>
);

export default function Header() {
  const contact = NAV_ITEMS.find((i) => i.label === "CONTACT")!;
  const main    = NAV_ITEMS.filter((i) => i.label !== "CONTACT");

  return (
    <header className="flexJIC w-full bg-[var(--background)]">
      <div className="flex w-full items-center justify-between">
        <a className="hover:underline hover:underline-offset-4" href="https://tw3partners.fr/fr/accueil/" target="_blank" rel="noopener noreferrer">
          <Image src="/logo.png" alt="Logo TW3 Partners" width={160} height={126} aria-hidden />
        </a>
        <nav className="flexJIC w-1/2 text-md text-white">
          {main.map(({ label, href }) => (
            <NavItem key={label} href={href}>{label}</NavItem>
          ))}
          <Resources />
          <NavItem href={contact.href}>{contact.label}</NavItem>
          <div className="w-full flexJIC gap-4">
            {LANG_FLAGS.map(({ src, alt, href }) => (
              <a key={alt} href={href} target="_blank" rel="noopener noreferrer">
                <Image src={src} alt={alt} width={20} height={15} aria-hidden />
              </a>
            ))}
          </div>
        </nav>
      </div>
    </header>
  );
}