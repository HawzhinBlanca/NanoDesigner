import { render, screen } from '@testing-library/react';
import {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardDescription,
  CardContent,
} from './card';

describe('Card', () => {
  it('renders a complete card with all sections', () => {
    render(
      <Card>
        <CardHeader>
          <CardTitle>Card Title</CardTitle>
          <CardDescription>Card Description</CardDescription>
        </CardHeader>
        <CardContent>
          <p>Card Content</p>
        </CardContent>
        <CardFooter>
          <p>Card Footer</p>
        </CardFooter>
      </Card>
    );

    // Check for title, description, content, and footer text
    expect(screen.getByText('Card Title')).toBeInTheDocument();
    expect(screen.getByText('Card Description')).toBeInTheDocument();
    expect(screen.getByText('Card Content')).toBeInTheDocument();
    expect(screen.getByText('Card Footer')).toBeInTheDocument();

    // Check that the main card component has its base class
    const cardElement = screen.getByText('Card Title').closest('.rounded-lg');
    expect(cardElement).toBeInTheDocument();
    expect(cardElement).toHaveClass('border', 'bg-white', 'shadow-sm');
  });

  it('renders only the content when other sections are not provided', () => {
    render(
      <Card>
        <CardContent>
          <p>Just content</p>
        </CardContent>
      </Card>
    );

    expect(screen.getByText('Just content')).toBeInTheDocument();
    expect(screen.queryByText('Card Title')).not.toBeInTheDocument();
  });
});
