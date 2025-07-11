import PropTypes from "prop-types";
import UnifiedModal from "../../components/common/UnifiedModal";

const KeyboardShortcutsModal = ({ isOpen, onClose }) => {
  const shortcuts = [
    { key: "⌘ + /", description: "Open keyboard shortcuts" },
    { key: "⌘ + K", description: "Open command palette" },
    { key: "N", description: "New chat" },
    { key: "⌘ + J", description: "Focus chat input" },
    { key: "⌘ + Shift + E", description: "Export chat" },
    { key: "⌘ + Shift + P", description: "Toggle project sidebar" },
    { key: "⌘ + Shift + S", description: "Toggle system prompt" },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Keyboard Shortcuts">
      <div className="grid grid-cols-2 gap-4">
        {shortcuts.map((shortcut) => (
          <div key={shortcut.key} className="flex items-center space-x-4">
            <kbd className="px-2 py-1.5 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-lg">
              {shortcut.key}
            </kbd>
            <span className="text-sm text-gray-600">
              {shortcut.description}
            </span>
          </div>
        ))}
      </div>
    </Modal>
  );
};

KeyboardShortcutsModal.propTypes = {
  isOpen: PropTypes.bool.isRequired,
  onClose: PropTypes.func.isRequired,
};

export default KeyboardShortcutsModal;
