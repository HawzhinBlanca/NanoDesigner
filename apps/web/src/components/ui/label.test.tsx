import { render, screen } from '@testing-library/react';
import { Label } from './label';
import { Input } from './input';

describe('Label', () => {
  it('renders the label with text', () => {
    render(<Label>Username</Label>);
    const label = screen.getByText('Username');
    expect(label).toBeInTheDocument();
  });

  it('associates with an input field', () => {
    render(
      <div>
        <Label htmlFor="username-input">Username</Label>
        <Input id="username-input" />
      </div>
    );

    const label = screen.getByText('Username');
    expect(label).toBeInTheDocument();

    const input = screen.getByLabelText('Username');
    expect(input).toBeInTheDocument();
  });
});
