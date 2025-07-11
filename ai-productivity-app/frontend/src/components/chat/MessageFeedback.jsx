import React, { useState } from "react";
import { ThumbsUp, ThumbsDown, Star, MessageSquare, X } from "lucide-react";
import { Button } from "../common/Button";

const MessageFeedback = ({
  messageId,
  onFeedbackSubmit,
  initialFeedback = null,
  className = "",
}) => {
  const [showDetailedForm, setShowDetailedForm] = useState(false);
  const [feedback, setFeedback] = useState({
    rating: initialFeedback?.rating || 0,
    helpful: initialFeedback?.helpful || null,
    comments: initialFeedback?.comments || "",
    accuracy_rating: initialFeedback?.accuracy_rating || 0,
    clarity_rating: initialFeedback?.clarity_rating || 0,
    completeness_rating: initialFeedback?.completeness_rating || 0,
  });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleQuickFeedback = async (helpful) => {
    setIsSubmitting(true);
    try {
      const feedbackData = {
        message_id: messageId,
        rating: helpful ? 1 : -1,
        helpful: helpful,
      };

      await onFeedbackSubmit(feedbackData);
      setFeedback((prev) => ({ ...prev, helpful, rating: helpful ? 1 : -1 }));
    } catch (error) {
      console.error("Failed to submit feedback:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDetailedSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const feedbackData = {
        message_id: messageId,
        ...feedback,
      };

      await onFeedbackSubmit(feedbackData);
      setShowDetailedForm(false);
    } catch (error) {
      console.error("Failed to submit detailed feedback:", error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const StarRating = ({ value, onChange, label }) => (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-600 w-20">{label}:</span>
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            className={`p-1 ${
              star <= value
                ? "text-yellow-400 hover:text-yellow-500"
                : "text-gray-300 hover:text-gray-400"
            }`}
          >
            <Star size={16} fill={star <= value ? "currentColor" : "none"} />
          </button>
        ))}
      </div>
    </div>
  );

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {/* Quick Feedback Buttons */}
      <div className="flex items-center gap-1">
        <Button
          variant={feedback.helpful === true ? "primary" : "ghost"}
          size="sm"
          onClick={() => handleQuickFeedback(true)}
          disabled={isSubmitting}
          className="p-1.5"
          title="This was helpful"
        >
          <ThumbsUp size={14} />
        </Button>

        <Button
          variant={feedback.helpful === false ? "destructive" : "ghost"}
          size="sm"
          onClick={() => handleQuickFeedback(false)}
          disabled={isSubmitting}
          className="p-1.5"
          title="This was not helpful"
        >
          <ThumbsDown size={14} />
        </Button>
      </div>

      {/* Detailed Feedback Toggle */}
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setShowDetailedForm(!showDetailedForm)}
        className="p-1.5"
        title="Provide detailed feedback"
      >
        <MessageSquare size={14} />
      </Button>

      {/* Current Feedback Status */}
      {feedback.helpful !== null && (
        <span className="text-xs text-gray-500">
          {feedback.helpful ? "Marked helpful" : "Marked not helpful"}
        </span>
      )}

      {/* Detailed Feedback Form */}
      {showDetailedForm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Detailed Feedback</h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowDetailedForm(false)}
                className="p-1"
              >
                <X size={16} />
              </Button>
            </div>

            <form onSubmit={handleDetailedSubmit} className="space-y-4">
              {/* Overall Rating */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Overall Rating
                </label>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      type="button"
                      onClick={() =>
                        setFeedback((prev) => ({ ...prev, rating: star }))
                      }
                      className={`p-1 ${
                        star <= feedback.rating
                          ? "text-yellow-400 hover:text-yellow-500"
                          : "text-gray-300 hover:text-gray-400"
                      }`}
                    >
                      <Star
                        size={20}
                        fill={star <= feedback.rating ? "currentColor" : "none"}
                      />
                    </button>
                  ))}
                </div>
              </div>

              {/* Detailed Ratings */}
              <div className="space-y-2">
                <StarRating
                  value={feedback.accuracy_rating}
                  onChange={(value) =>
                    setFeedback((prev) => ({ ...prev, accuracy_rating: value }))
                  }
                  label="Accuracy"
                />
                <StarRating
                  value={feedback.clarity_rating}
                  onChange={(value) =>
                    setFeedback((prev) => ({ ...prev, clarity_rating: value }))
                  }
                  label="Clarity"
                />
                <StarRating
                  value={feedback.completeness_rating}
                  onChange={(value) =>
                    setFeedback((prev) => ({
                      ...prev,
                      completeness_rating: value,
                    }))
                  }
                  label="Complete"
                />
              </div>

              {/* Comments */}
              <div>
                <label className="block text-sm font-medium mb-2">
                  Comments (optional)
                </label>
                <textarea
                  value={feedback.comments}
                  onChange={(e) =>
                    setFeedback((prev) => ({
                      ...prev,
                      comments: e.target.value,
                    }))
                  }
                  placeholder="Tell us what was helpful or how we could improve..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                />
              </div>

              {/* Submit Button */}
              <div className="flex justify-end gap-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowDetailedForm(false)}
                  disabled={isSubmitting}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting || feedback.rating === 0}
                >
                  {isSubmitting ? "Submitting..." : "Submit Feedback"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default MessageFeedback;
