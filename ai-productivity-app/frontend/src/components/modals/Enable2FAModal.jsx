import PropTypes from 'prop-types';
import Modal from '../common/Modal';

const Enable2FAModal = ({ isOpen, onClose }) => {

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Enable Two-Factor Authentication">
      <div className="space-y-4 p-4 text-center">
        <h3 className="text-lg font-medium text-gray-900">Feature Coming Soon</h3>
        <p className="mt-2 text-sm text-gray-500">
          Two-factor authentication is not yet available. We are working on implementing this feature to enhance your account security.
        </p>
        <div className="mt-6">
          <button
            type="button"
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
};

Enable2FAModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default Enable2FAModal;
