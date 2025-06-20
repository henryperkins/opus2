import PropTypes from 'prop-types';
import Modal from '../common/Modal';

const DocumentationModal = ({ isOpen, onClose }) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Documentation">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Welcome to the AI Productivity App documentation. Here you will find information on how to use the app and its features.
        </p>
        <div>
          <h4 className="font-semibold text-gray-800">Getting Started</h4>
          <p className="mt-1 text-sm text-gray-600">
            To start a new chat, click the "New Chat" button in the sidebar. You can then type your message in the input box at the bottom of the screen.
          </p>
        </div>
        <div>
          <h4 className="font-semibold text-gray-800">Projects</h4>
          <p className="mt-1 text-sm text-gray-600">
            Projects allow you to organize your chats and files. You can create a new project from the sidebar. Once a project is created, you can add chats and upload files to it.
          </p>
        </div>
        <div>
          <h4 className="font-semibold text-gray-800">Search</h4>
          <p className="mt-1 text-sm text-gray-600">
            The search functionality allows you to search across all your chats and documents. You can access the search page from the sidebar.
          </p>
        </div>
        <p className="text-sm text-gray-600">
          For more detailed documentation, please visit our official documentation website.
        </p>
      </div>
    </Modal>
  );
};

DocumentationModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default DocumentationModal;
