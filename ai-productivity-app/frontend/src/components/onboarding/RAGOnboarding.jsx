import React, { useState } from 'react';
import { Button } from '../common/Button';
import { Modal } from '../common/Modal';
import { Brain, Upload, Search, MessageCircle, CheckCircle, ArrowRight } from 'lucide-react';

const RAG_ONBOARDING_STEPS = [
  {
    id: 'welcome',
    title: "Welcome to AI-Powered Knowledge",
    icon: <Brain className="w-8 h-8 text-blue-600" />,
    content: "Your AI assistant can now search through your uploaded documents, code, and knowledge base to provide more accurate and contextual responses.",
    action: "Get Started",
    highlight: null
  },
  {
    id: 'upload',
    title: "Upload Your Knowledge",
    icon: <Upload className="w-8 h-8 text-green-600" />,
    content: "Start by uploading documents, connecting repositories, or adding knowledge entries. The more you add, the smarter your assistant becomes.",
    action: "Show Me How",
    highlight: ".knowledge-upload-area",
    tips: [
      "Upload PDFs, text files, and documentation",
      "Connect GitHub repositories for code context",
      "Add knowledge entries for procedures and guidelines"
    ]
  },
  {
    id: 'search',
    title: "Ask Knowledge-Aware Questions",
    icon: <MessageCircle className="w-8 h-8 text-purple-600" />,
    content: "Try asking questions like 'How does the authentication work?' or 'What's the deployment process?' - your assistant will search your knowledge base for answers.",
    action: "Try It",
    highlight: ".chat-input",
    examples: [
      "How do I deploy this application?",
      "What's the error handling approach?",
      "Where is the user authentication implemented?",
      "What are the coding standards for this project?"
    ]
  },
  {
    id: 'understand',
    title: "Understand RAG Responses",
    icon: <Search className="w-8 h-8 text-orange-600" />,
    content: "Look for the RAG status indicator and citations to see what sources informed each response. You can click citations to view the original content.",
    action: "Got It",
    highlight: ".rag-status-indicator",
    features: [
      "Green indicator shows RAG is active",
      "Confidence percentage shows source reliability",
      "Citations link to original documents",
      "Click citations to view source content"
    ]
  }
];

export const RAGOnboarding = ({ isOpen, onComplete, onSkip }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [highlightElement, setHighlightElement] = useState(null);
  
  const currentStepData = RAG_ONBOARDING_STEPS[currentStep];
  const isLastStep = currentStep === RAG_ONBOARDING_STEPS.length - 1;

  const handleNext = () => {
    if (isLastStep) {
      onComplete();
    } else {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSkip = () => {
    onSkip();
  };

  // Highlight element when step has a highlight target
  React.useEffect(() => {
    if (currentStepData.highlight && isOpen) {
      const element = document.querySelector(currentStepData.highlight);
      if (element) {
        setHighlightElement(element);
        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
        element.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.5)';
        element.style.borderRadius = '8px';
        element.style.transition = 'box-shadow 0.3s ease';
      }
    }
    
    return () => {
      if (highlightElement) {
        highlightElement.style.boxShadow = '';
        highlightElement.style.borderRadius = '';
      }
    };
  }, [currentStep, currentStepData.highlight, isOpen, highlightElement]);

  if (!isOpen) return null;

  return (
    <Modal isOpen={isOpen} onClose={handleSkip} className="max-w-2xl">
      <div className="p-6">
        {/* Progress indicator */}
        <div className="mb-6">
          <div className="flex justify-between items-center mb-3">
            <h2 className="text-xl font-semibold text-gray-900">
              Getting Started with RAG
            </h2>
            <span className="text-sm text-gray-500">
              {currentStep + 1} of {RAG_ONBOARDING_STEPS.length}
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-500 ease-out"
              style={{ width: `${((currentStep + 1) / RAG_ONBOARDING_STEPS.length) * 100}%` }}
            />
          </div>
        </div>

        {/* Step content */}
        <div className="mb-8">
          <div className="flex items-start gap-4 mb-4">
            <div className="flex-shrink-0">
              {currentStepData.icon}
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {currentStepData.title}
              </h3>
              <p className="text-gray-600 text-base leading-relaxed">
                {currentStepData.content}
              </p>
            </div>
          </div>

          {/* Tips section */}
          {currentStepData.tips && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 mt-4">
              <h4 className="font-medium text-green-800 mb-2">Tips:</h4>
              <ul className="space-y-1">
                {currentStepData.tips.map((tip, index) => (
                  <li key={index} className="flex items-center text-green-700 text-sm">
                    <CheckCircle className="w-4 h-4 mr-2 flex-shrink-0" />
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Examples section */}
          {currentStepData.examples && (
            <div className="bg-purple-50 border border-purple-200 rounded-lg p-4 mt-4">
              <h4 className="font-medium text-purple-800 mb-3">Try asking:</h4>
              <div className="grid grid-cols-1 gap-2">
                {currentStepData.examples.map((example, index) => (
                  <div key={index} className="bg-white border border-purple-200 rounded-md p-2 text-sm text-purple-700">
                    "{example}"
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Features section */}
          {currentStepData.features && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 mt-4">
              <h4 className="font-medium text-orange-800 mb-2">What to look for:</h4>
              <ul className="space-y-1">
                {currentStepData.features.map((feature, index) => (
                  <li key={index} className="flex items-center text-orange-700 text-sm">
                    <ArrowRight className="w-4 h-4 mr-2 flex-shrink-0" />
                    {feature}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex justify-between items-center">
          <div className="flex gap-2">
            <Button 
              variant="outline" 
              onClick={handlePrevious}
              disabled={currentStep === 0}
              className="px-4 py-2"
            >
              Previous
            </Button>
            <Button 
              variant="outline" 
              onClick={handleSkip}
              className="px-4 py-2 text-gray-600"
            >
              Skip Tour
            </Button>
          </div>
          
          <Button 
            onClick={handleNext}
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white"
          >
            {isLastStep ? "Let's Start!" : currentStepData.action}
            {!isLastStep && <ArrowRight className="w-4 h-4 ml-2" />}
          </Button>
        </div>

        {/* Step indicators */}
        <div className="flex justify-center mt-6 space-x-2">
          {RAG_ONBOARDING_STEPS.map((_, index) => (
            <button
              key={index}
              onClick={() => setCurrentStep(index)}
              className={`w-3 h-3 rounded-full transition-colors duration-200 ${
                index === currentStep 
                  ? 'bg-blue-600' 
                  : index < currentStep 
                    ? 'bg-green-500' 
                    : 'bg-gray-300'
              }`}
              aria-label={`Go to step ${index + 1}`}
            />
          ))}
        </div>
      </div>
    </Modal>
  );
};

export default RAGOnboarding;