// Tests unitaires pour le frontend TW3

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { jest } from '@jest/globals'
import Home from '../src/pages/index'

// Mock fetch globally
global.fetch = jest.fn()

// Mock next/router
jest.mock('next/router', () => ({
  useRouter: () => ({
    push: jest.fn(),
    pathname: '/',
  }),
}))

describe('TW3 Chat Application', () => {
  beforeEach(() => {
    fetch.mockClear()
  })

  describe('Page d\'accueil', () => {
    test('affiche le titre du chatbot', () => {
      render(<Home />)
      expect(screen.getByText('TW3 Qwen Chatbot')).toBeInTheDocument()
    })

    test('affiche la zone de saisie', () => {
      render(<Home />)
      const input = screen.getByPlaceholderText('Votre message...')
      expect(input).toBeInTheDocument()
    })

    test('affiche le bouton d\'envoi', () => {
      render(<Home />)
      const button = screen.getByRole('button', { name: /envoyer/i })
      expect(button).toBeInTheDocument()
    })
  })

  describe('Envoi de messages', () => {
    test('envoie un message quand on clique sur le bouton', async () => {
      const mockResponse = {
        conv_id: 'test-conv-id',
        answer: 'Réponse de test'
      }
      
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      })

      render(<Home />)
      
      const input = screen.getByPlaceholderText('Votre message...')
      const button = screen.getByRole('button', { name: /envoyer/i })
      
      fireEvent.change(input, { target: { value: 'Test message' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(fetch).toHaveBeenCalledWith(
          expect.stringContaining('/ask'),
          expect.objectContaining({
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
              question: 'Test message', 
              conv_id: null 
            }),
          })
        )
      })
    })

    test('affiche le message de l\'utilisateur immédiatement', async () => {
      render(<Home />)
      
      const input = screen.getByPlaceholderText('Votre message...')
      const button = screen.getByRole('button', { name: /envoyer/i })
      
      fireEvent.change(input, { target: { value: 'Message utilisateur' } })
      fireEvent.click(button)

      expect(screen.getByText('Message utilisateur')).toBeInTheDocument()
    })

    test('vide le champ de saisie après envoi', async () => {
      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ conv_id: 'test', answer: 'test' }),
      })

      render(<Home />)
      
      const input = screen.getByPlaceholderText('Votre message...')
      const button = screen.getByRole('button', { name: /envoyer/i })
      
      fireEvent.change(input, { target: { value: 'Test message' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(input.value).toBe('')
      })
    })
  })

  describe('Gestion des erreurs', () => {
    test('affiche un message d\'erreur en cas d\'échec de connexion', async () => {
      fetch.mockRejectedValueOnce(new Error('Erreur de connexion'))

      render(<Home />)
      
      const input = screen.getByPlaceholderText('Votre message...')
      const button = screen.getByRole('button', { name: /envoyer/i })
      
      fireEvent.change(input, { target: { value: 'Test message' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(screen.getByText(/❌ Erreur de connexion au serveur/)).toBeInTheDocument()
      })
    })

    test('affiche un message d\'erreur pour une réponse HTTP non-ok', async () => {
      fetch.mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      })

      render(<Home />)
      
      const input = screen.getByPlaceholderText('Votre message...')
      const button = screen.getByRole('button', { name: /envoyer/i })
      
      fireEvent.change(input, { target: { value: 'Test message' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(screen.getByText(/❌ Erreur de connexion au serveur/)).toBeInTheDocument()
      })
    })
  })

  describe('État de chargement', () => {
    test('affiche un indicateur de loading pendant la requête', async () => {
      let resolvePromise
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      
      fetch.mockReturnValueOnce(promise)

      render(<Home />)
      
      const input = screen.getByPlaceholderText('Votre message...')
      const button = screen.getByRole('button', { name: /envoyer/i })
      
      fireEvent.change(input, { target: { value: 'Test message' } })
      fireEvent.click(button)

      // Vérifier que l'indicateur de loading est présent
      expect(screen.getByTestId('typing-loader')).toBeInTheDocument()

      // Résoudre la promesse
      resolvePromise({
        ok: true,
        json: async () => ({ conv_id: 'test', answer: 'test' }),
      })

      await waitFor(() => {
        expect(screen.queryByTestId('typing-loader')).not.toBeInTheDocument()
      })
    })
  })

  describe('Gestion de conversation', () => {
    test('utilise le conv_id pour les messages suivants', async () => {
      const firstResponse = {
        conv_id: 'test-conv-123',
        answer: 'Première réponse'
      }
      
      const secondResponse = {
        conv_id: 'test-conv-123',
        answer: 'Deuxième réponse'
      }

      fetch
        .mockResolvedValueOnce({
          ok: true,
          json: async () => firstResponse,
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => secondResponse,
        })

      render(<Home />)
      
      const input = screen.getByPlaceholderText('Votre message...')
      const button = screen.getByRole('button', { name: /envoyer/i })
      
      // Premier message
      fireEvent.change(input, { target: { value: 'Premier message' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(screen.getByText('Première réponse')).toBeInTheDocument()
      })

      // Deuxième message
      fireEvent.change(input, { target: { value: 'Deuxième message' } })
      fireEvent.click(button)

      await waitFor(() => {
        expect(fetch).toHaveBeenLastCalledWith(
          expect.stringContaining('/ask'),
          expect.objectContaining({
            body: JSON.stringify({ 
              question: 'Deuxième message', 
              conv_id: 'test-conv-123' 
            }),
          })
        )
      })
    })
  })
})
