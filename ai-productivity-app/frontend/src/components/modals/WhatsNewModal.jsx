import PropTypes from 'prop-types';
import Modal from '../common/Modal';

const WhatsNewModal = ({ isOpen, onClose }) => {
  const features = [
    {
      version: 'v1.2.0',
      date: '2025-06-20',
      title: 'New Sidebar and UI Enhancements',
      description: 'A brand new, modern sidebar for improved navigation and a cleaner user experience. Inspired by Claude.ai, it includes sections for recent chats, projects, and settings.',
    },
    {
      version: 'v1.1.0',
      date: '2025-06-15',
      title: 'Project Management',
      description: 'You can now create, archive, and manage your projects directly within the app.',
    },
    {
      version: 'v1.0.0',
      date: '2025-06-01',
      title: 'Initial Release',
      description: 'The first version of the AI Productivity App, featuring core chat and search functionalities.',
    },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="What's New">
      <div className="space-y-6">
        {features.map((feature) => (
          <div key={feature.version}>
            <div className="flex items-center space-x-3">
              <span className="px-2 py-1 text-xs font-semibold text-white bg-blue-500 rounded-full">
                {feature.version}
              </span>
              <h3 className="text-lg font-semibold text-gray-800">{feature.title}</h3>
              <span className="text-sm text-gray-500">{feature.date}</span>
            </div>
            <p className="mt-2 text-sm text-gray-600">{feature.description}</p>
          </div>
        ))}
      </div>
    </Modal>
  );
};

WhatsNewModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default WhatsNewModal;
