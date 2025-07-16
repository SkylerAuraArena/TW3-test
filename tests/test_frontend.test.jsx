/* Tests unitaires pour le frontend TW3 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import { jest } from '@jest/globals'
import Home from '../docker/images/frontend/src/pages/index'

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
        expect(screen.getByText(/ERROR: Connection error to server/)).toBeInTheDocument()
      })
    })
  })
})
