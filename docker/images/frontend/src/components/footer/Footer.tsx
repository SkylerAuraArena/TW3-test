import React from 'react';
import Image from "next/image";

const Footer: React.FC = () => {
    return (
        <footer className="flexJIC w-full fixed bottom-0 pb-14 pt-1 bg-[var(--background)]">
            <div className="flex items-center justify-between w-full pt-12 pl-5 pr-5">
                <div className='flex justify-center items-start gap-12'>
                    <div className="flex justify-between items-stretch flex-col">
                        <a className="hover:underline hover:underline-offset-4" href="https://tw3partners.fr/fr/accueil/" target="_blank" rel="noopener noreferrer" > 
                        <Image aria-hidden src="/logo.png" alt="Logo TW3 Partners" width={220} height={126}/>
                        </a>
                        <div className="flex JIC gap-3">
                            <p className="text-white">Suivez-nous</p>
                            <a href="https://www.linkedin.com/company/tw3partners/" target="_blank">
                                <svg className="e-font-icon-svg e-fab-linkedin text-white w-6 h-6" fill="White" viewBox="0 0 448 512" xmlns="http://www.w3.org/2000/svg">
                                <path d="M416 32H31.9C14.3 32 0 46.5 0 64.3v383.4C0 465.5 14.3 480 31.9 480H416c17.6 0 32-14.5 32-32.3V64.3c0-17.8-14.4-32.3-32-32.3zM135.4 416H69V202.2h66.5V416zm-33.2-243c-21.3 0-38.5-17.3-38.5-38.5S80.9 96 102.2 96c21.2 0 38.5 17.3 38.5 38.5 0 21.3-17.2 38.5-38.5 38.5zm282.1 243h-66.4V312c0-24.8-.5-56.7-34.5-56.7-34.6 0-39.9 27-39.9 54.9V416h-66.4V202.2h63.7v29.2h.9c8.9-16.8 30.6-34.5 62.9-34.5 67.2 0 79.7 44.3 79.7 101.9V416z"></path>
                                </svg>
                            </a>
                            <a href="https://www.youtube.com/@TW3Partners" target="_blank">
                                <svg className="w-6 h-6 text-white" fill="White" viewBox="0 0 576 512" xmlns="http://www.w3.org/2000/svg"><path d="M549.655 124.083c-6.281-23.65-24.787-42.276-48.284-48.597C458.781 64 288 64 288 64S117.22 64 74.629 75.486c-23.497 6.322-42.003 24.947-48.284 48.597-11.412 42.867-11.412 132.305-11.412 132.305s0 89.438 11.412 132.305c6.281 23.65 24.787 41.5 48.284 47.821C117.22 448 288 448 288 448s170.78 0 213.371-11.486c23.497-6.321 42.003-24.171 48.284-47.821 11.412-42.867 11.412-132.305 11.412-132.305s0-89.438-11.412-132.305zm-317.51 213.508V175.185l142.739 81.205-142.739 81.201z"></path></svg>					
                            </a>
                        </div>
                </div>
                    <div className="flex items-start justify-center flex-col">
                        <div className="flex items-start justify-center flex-col text-3xl text-[var(--tw3blue)]">
                        <span>
                            Inscrivez-vous à notre
                        </span>
                        <b>Newsletter</b>
                        </div>
                        <span className="text-white text-xl">
                        Perspectives
                        </span>
                        <button className="rounded-full border border-solid border-transparent transition-colors flexJIC bg-[var(--tw3blue)] text-background gap-2 hover:bg-white font-medium text-sm sm:text-base h-6 sm:h-8 px-4 sm:px-5 sm:w-auto">
                            <a href="https://www.linkedin.com/newsletters/tw3-partners-perspectives-7136399002597482496/" target="_blank" rel="noopener noreferrer">
                                {`S'abonner sur LinkedIn`}
                            </a>
                        </button>
                    </div>
                </div>
                <div className="flex justify-center items-end flex-col gap-2 text-[10px]">
                    <div className="flexJIC gap-4 font-extrabold text-[var(--tw3grey)]">
                        <a href="https://tw3partners.fr/fr/conditions-generales-de-services/">Conditions Générales De Services</a>
                        <a href="https://tw3partners.fr/fr/mentions-legales/">Mentions Légales</a>
                        <a href="https://tw3partners.fr/fr/politique-de-confidentialite/">Politique de Confidentialité</a>
                    </div>
                    <div>
                    <span className="text-gray-400">{`TW3 Partners - Capital 10'000€ - © 2025 Tous droits réservés`}</span>
                    </div>
                </div>
            </div>
        </footer>
    );
};

export default Footer;