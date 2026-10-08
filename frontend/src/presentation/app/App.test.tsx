import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { App } from './App'

describe('App', () => {
  it('renders the platform name', () => {
    render(<App />)
    expect(screen.getByText('Knowledge Intelligence Platform')).toBeInTheDocument()
  })
})
