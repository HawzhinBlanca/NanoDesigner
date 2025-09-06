import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Textarea } from './textarea';

describe('Textarea', () => {
  it('renders the textarea with a placeholder', () => {
    render(<Textarea placeholder="Enter text..." />);
    const textarea = screen.getByPlaceholderText('Enter text...');
    expect(textarea).toBeInTheDocument();
  });

  it('allows user to type in the textarea', async () => {
    const user = userEvent.setup();
    render(<Textarea />);
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, 'Hello, world!');
    expect(textarea).toHaveValue('Hello, world!');
  });

  it('is disabled when the disabled prop is true', () => {
    render(<Textarea disabled />);
    const textarea = screen.getByRole('textbox');
    expect(textarea).toBeDisabled();
  });
});
