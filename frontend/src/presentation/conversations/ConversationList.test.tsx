import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConversationList } from './ConversationList'

describe('ConversationList', () => {
  it('renders each conversation and calls onSelect when clicked', async () => {
    const onSelect = vi.fn()
    render(
      <ConversationList
        conversations={[{ id: 'c1' }, { id: 'c2' }]}
        activeConversationId="c1"
        onSelect={onSelect}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'c2' }))
    expect(onSelect).toHaveBeenCalledWith('c2')
  })
})
