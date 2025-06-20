import { useState } from 'react';
import PropTypes from 'prop-types';
import Modal from '../common/Modal';

const Enable2FAModal = ({ isOpen, onClose }) => {
  const [qrCode, setQrCode] = useState('');
  const [verificationCode, setVerificationCode] = useState('');

  // In a real app, you would generate a QR code from the backend
  useState(() => {
    setQrCode('https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=otpauth://totp/AI-Productivity-App:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=AI-Productivity-App');
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    // Handle 2FA verification logic here
    console.log('Verifying 2FA code...');
    onClose();
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Enable Two-Factor Authentication">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Scan the QR code with your authenticator app and enter the verification code below.
        </p>
        <div className="flex justify-center">
          {qrCode && <img src={qrCode} alt="QR Code" />}
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Verification Code</label>
            <input
              type="text"
              value={verificationCode}
              onChange={(e) => setVerificationCode(e.target.value)}
              className="mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              required
            />
          </div>
          <div className="flex justify-end space-x-2">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
              Cancel
            </button>
            <button type="submit" className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
              Verify & Enable
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
};

Enable2FAModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default Enable2FAModal;
