import { test, expect } from '@playwright/experimental-ct-react';
import { MainContent } from '../../src/components/main-content';
import { MOCK_PROJECTS, MOCK_RECENT_TICKETS_SUCCESS } from './mock-data'; // Import MOCK_PROJECTS

test.use({ viewport: { width: 1000, height: 800 } }); // Adjust viewport for better visibility

const defaultProps = {
  projects: MOCK_PROJECTS,
  selectedProject: 'PROJ',
  setSelectedProject: () => {},
  title: '',
  setTitle: () => {},
  description: '',
  setDescription: () => {},
  loading: false,
  findingError: undefined,
  recentTickets: [],
  handleCreateTicket: () => {},
  handleTriggerBlogDigest: () => {},
  fetchRecentTickets: () => {}, // No-op for component tests
};

test('should display recent tickets on successful data provision', async ({ mount }) => {
  const component = await mount(<MainContent {...defaultProps} recentTickets={MOCK_RECENT_TICKETS_SUCCESS} />);
  await expect(component.getByText('Recent Tickets')).toBeVisible();
  await expect(component.getByText('Ticket 1 Summary')).toBeVisible();
  await expect(component.getByText('Ticket 2 Summary')).toBeVisible();
});

test('should display no tickets message when recentTickets prop is empty', async ({ mount }) => {
  const component = await mount(<MainContent {...defaultProps} recentTickets={[]} />);
  await expect(component.getByText('Recent Tickets')).toBeVisible();
  await expect(component.getByText('No tickets found for this project.')).toBeVisible();
});

test('should display error message when findingError prop is set', async ({ mount }) => {
  const component = await mount(<MainContent {...defaultProps} findingError="Failed to submit finding." />);
  await expect(component.getByText('Failed to submit finding.')).toBeVisible();
});

// Test for the scenario where fetchRecentTickets is called (e.g., via Refresh button)
test('should call fetchRecentTickets when Refresh button is clicked', async ({ mount, page }) => {
  let callCount = 0;
  const fetchRecentTicketsMock = () => {
    callCount++;
  };
  const component = await mount(<MainContent {...defaultProps} fetchRecentTickets={fetchRecentTicketsMock} />);
  
  await component.getByRole('button', { name: 'Refresh' }).click();
  expect(callCount).toBe(1); // Assert on the callCount
});
