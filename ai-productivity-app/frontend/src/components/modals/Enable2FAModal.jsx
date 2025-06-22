import { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import Modal from '../common/Modal';
import { authAPI } from '../../api/auth';
import { toast } from '../common/Toast';
import { copyToClipboard } from '../../utils/clipboard';
import { QrCode, Shield, Copy, CheckCircle, AlertCircle } from 'lucide-react';

const Enable2FAModal = ({ isOpen, onClose, onSuccess }) => {
  const [step, setStep] = useState(1);
  const [qrCodeData, setQrCodeData] = useState(null);
  const [secret, setSecret] = useState('');
  const [backupCodes, setBackupCodes] = useState([]);
  const [verificationCode, setVerificationCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Step 1: Generate QR code and secret
  const setup2FA = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const response = await authAPI.setup2FA();
      setQrCodeData(response.qr_code);
      setSecret(response.secret);
      setBackupCodes(response.backup_codes);
      setStep(2);
    } catch (error) {
      console.error('Failed to setup 2FA:', error);
      setError('Failed to generate 2FA setup. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  // Step 2: Verify the setup
  const verify2FA = async () => {
    if (!verificationCode || verificationCode.length !== 6) {
      setError('Please enter a valid 6-digit code');
      return;
    }

    setIsLoading(true);
    setError('');
    
    try {
      await authAPI.verify2FA(verificationCode);
      setStep(3);
      toast.success('Two-factor authentication enabled successfully!');
    } catch (error) {
      console.error('Failed to verify 2FA:', error);
      if (error.response?.status === 400) {
        setError('Invalid verification code. Please try again.');
      } else {
        setError('Verification failed. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };


  const downloadBackupCodes = () => {
    const content = backupCodes.join('\n');
    const blob = new window.Blob([content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = '2fa-backup-codes.txt';
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleClose = () => {
    setStep(1);
    setQrCodeData(null);
    setSecret('');
    setBackupCodes([]);
    setVerificationCode('');
    setError('');
    onClose();
  };

  const handleComplete = () => {
    if (onSuccess) onSuccess();
    handleClose();
  };

  useEffect(() => {
    if (isOpen && step === 1) {
      setup2FA();
    }
  }, [isOpen, step]);

  const renderStep1 = () => (
    <div className="space-y-4 text-center">
      <div className="flex items-center justify-center w-16 h-16 mx-auto bg-blue-100 rounded-full">
        <Shield className="w-8 h-8 text-blue-600" />
      </div>
      <h3 className="text-lg font-medium text-gray-900">Setting up Two-Factor Authentication</h3>
      <p className="text-sm text-gray-500">
        Generating your unique QR code and secret key...
      </p>
      {isLoading && (
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
      )}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-md">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );

  const renderStep2 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <h3 className="text-lg font-medium text-gray-900">Scan QR Code</h3>
        <p className="mt-2 text-sm text-gray-500">
          Use your authenticator app (Google Authenticator, Authy, etc.) to scan this QR code
        </p>
      </div>

      {/* QR Code */}
      <div className="flex justify-center">
        {qrCodeData ? (
          <div className="p-4 bg-white border-2 border-gray-200 rounded-lg">
            <img src={qrCodeData} alt="2FA QR Code" className="w-48 h-48" />
          </div>
        ) : (
          <div className="flex items-center justify-center w-48 h-48 bg-gray-100 border-2 border-gray-200 rounded-lg">
            <QrCode className="w-16 h-16 text-gray-400" />
          </div>
        )}
      </div>

      {/* Manual Entry Option */}
      <div className="bg-gray-50 p-4 rounded-lg">
        <p className="text-sm font-medium text-gray-700 mb-2">Can't scan? Enter this code manually:</p>
        <div className="flex items-center justify-between bg-white p-3 border rounded-md">
          <code className="text-sm font-mono text-gray-800 break-all">{secret}</code>
          <button
            onClick={() => copyToClipboard(secret)}
            className="ml-2 p-1 text-gray-500 hover:text-gray-700"
            title="Copy to clipboard"
          >
            <Copy className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Verification */}
      <div className="space-y-3">
        <label className="block text-sm font-medium text-gray-700">
          Enter verification code from your authenticator app:
        </label>
        <input
          type="text"
          value={verificationCode}
          onChange={(e) => {
            const value = e.target.value.replace(/\D/g, '').slice(0, 6);
            setVerificationCode(value);
            setError('');
          }}
          placeholder="123456"
          className="block w-full px-3 py-2 text-center text-lg font-mono border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          maxLength={6}
        />
        {error && (
          <div className="flex items-center space-x-2 text-sm text-red-600">
            <AlertCircle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}
      </div>

      <div className="flex justify-end space-x-3">
        <button
          type="button"
          onClick={handleClose}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md shadow-sm hover:bg-gray-50"
        >
          Cancel
        </button>
        <button
          onClick={verify2FA}
          disabled={isLoading || verificationCode.length !== 6}
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md shadow-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Verifying...' : 'Verify & Enable'}
        </button>
      </div>
    </div>
  );

  const renderStep3 = () => (
    <div className="space-y-6">
      <div className="text-center">
        <div className="flex items-center justify-center w-16 h-16 mx-auto bg-green-100 rounded-full">
          <CheckCircle className="w-8 h-8 text-green-600" />
        </div>
        <h3 className="mt-4 text-lg font-medium text-gray-900">2FA Enabled Successfully!</h3>
        <p className="mt-2 text-sm text-gray-500">
          Your account is now protected with two-factor authentication
        </p>
      </div>

      {/* Backup Codes */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <div className="flex items-start space-x-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5" />
          <div className="flex-1">
            <h4 className="text-sm font-medium text-yellow-800">Save Your Backup Codes</h4>
            <p className="text-sm text-yellow-700 mt-1">
              These backup codes can be used to access your account if you lose your authenticator device. 
              Store them in a safe place.
            </p>
          </div>
        </div>
      </div>

      <div className="bg-gray-50 p-4 rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-medium text-gray-700">Backup Codes</h4>
          <div className="space-x-2">
            <button
              onClick={() => copyToClipboard(backupCodes.join('\n'))}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              Copy All
            </button>
            <button
              onClick={downloadBackupCodes}
              className="text-xs text-blue-600 hover:text-blue-700"
            >
              Download
            </button>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {backupCodes.map((code, index) => (
            <div key={index} className="bg-white p-2 border rounded text-center">
              <code className="text-sm font-mono text-gray-800">{code}</code>
            </div>
          ))}
        </div>
      </div>

      <div className="flex justify-end">
        <button
          onClick={handleComplete}
          className="px-6 py-2 text-sm font-medium text-white bg-green-600 border border-transparent rounded-md shadow-sm hover:bg-green-700"
        >
          Complete Setup
        </button>
      </div>
    </div>
  );

  return (
    <Modal isOpen={isOpen} onClose={handleClose} title="Enable Two-Factor Authentication">
      <div className="p-4">
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </div>
    </Modal>
  );
};

Enable2FAModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
  onSuccess: PropTypes.func,
};

export default Enable2FAModal;
