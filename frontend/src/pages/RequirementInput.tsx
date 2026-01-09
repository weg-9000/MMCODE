/**
 * RequirementInput page
 * Input form for project requirements with rich text support
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText,
  Send,
  Loader2,
  Lightbulb,
  Upload,
  X,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useSessionStore, useUIStore } from '@/stores';
import { sessionService } from '@/services/sessionService';

/**
 * Example templates for requirements
 */
const exampleTemplates = [
  {
    title: 'E-commerce Platform',
    description: 'Online store with product catalog, cart, checkout, and user accounts',
  },
  {
    title: 'Task Management App',
    description: 'Project management tool with tasks, teams, deadlines, and progress tracking',
  },
  {
    title: 'Social Media Dashboard',
    description: 'Analytics dashboard for social media metrics with real-time data visualization',
  },
  {
    title: 'Healthcare Portal',
    description: 'Patient management system with appointments, records, and secure messaging',
  },
];

/**
 * RequirementInput page component
 */
export function RequirementInput() {
  const navigate = useNavigate();

  // Use individual selectors to prevent infinite re-renders
  const addNotification = useUIStore((state) => state.addNotification);
  const addSession = useSessionStore((state) => state.addSession);
  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);
  const setOrchestrationProgress = useSessionStore((state) => state.setOrchestrationProgress);

  // Form state
  const [projectName, setProjectName] = useState('');
  const [requirements, setRequirements] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);

  // Handle template selection
  const handleTemplateSelect = useCallback((template: typeof exampleTemplates[0]) => {
    setProjectName(template.title);
    setRequirements(
      `# ${template.title}\n\n## Overview\n${template.description}\n\n## Functional Requirements\n- \n\n## Non-Functional Requirements\n- \n\n## Target Users\n- \n\n## Constraints\n- `
    );
  }, []);

  // Handle file upload
  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    setUploadedFiles((prev) => [...prev, ...files]);
  }, []);

  // Remove uploaded file
  const handleRemoveFile = useCallback((index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  // Handle form submission
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!projectName.trim() || !requirements.trim()) {
      addNotification({
        type: 'error',
        title: 'Validation Error',
        message: 'Please provide both project name and requirements',
      });
      return;
    }

    setIsSubmitting(true);

    try {
      // Create session
      const session = await sessionService.createSession({
        title: projectName.trim(),
        description: requirements.substring(0, 200),
        requirements_text: requirements.trim(),
      });

      // Add to store
      addSession(session);
      setCurrentSession(session.id);

      // Initialize orchestration progress
      setOrchestrationProgress(session.id, {
        sessionId: session.id,
        status: 'idle',
        currentAgent: null,
        completedSteps: [],
        totalSteps: 4,
        artifacts: [],
      });

      addNotification({
        type: 'success',
        title: 'Project Created',
        message: `${projectName} has been created successfully`,
      });

      // Navigate to session view
      navigate(`/sessions/${session.id}`);
    } catch (error) {
      console.error('Failed to create session:', error);
      addNotification({
        type: 'error',
        title: 'Creation Failed',
        message: error instanceof Error ? error.message : 'Failed to create project',
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <h1 className="text-2xl font-semibold text-gray-900">New Project</h1>
        <p className="text-gray-500 mt-1">
          Describe your project requirements and let AI agents generate the
          architecture, technology stack, and documentation.
        </p>
      </motion.div>

      {/* Example Templates */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="mb-6"
      >
        <div className="flex items-center gap-2 mb-3">
          <Lightbulb className="h-4 w-4 text-amber-500" />
          <span className="text-sm font-medium text-gray-700">Start with a template</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {exampleTemplates.map((template) => (
            <button
              key={template.title}
              onClick={() => handleTemplateSelect(template)}
              className="p-3 bg-white rounded-lg border border-gray-200 text-left hover:border-primary-300 hover:shadow-sm transition-all group"
            >
              <h4 className="text-sm font-medium text-gray-900 group-hover:text-primary-600">
                {template.title}
              </h4>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {template.description}
              </p>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Form */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        onSubmit={handleSubmit}
        className="space-y-6"
      >
        {/* Project Name */}
        <div>
          <label
            htmlFor="projectName"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Project Name
          </label>
          <input
            type="text"
            id="projectName"
            value={projectName}
            onChange={(e) => setProjectName(e.target.value)}
            placeholder="My Awesome Project"
            className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            required
          />
        </div>

        {/* Requirements */}
        <div>
          <label
            htmlFor="requirements"
            className="block text-sm font-medium text-gray-700 mb-2"
          >
            Requirements
          </label>
          <textarea
            id="requirements"
            value={requirements}
            onChange={(e) => setRequirements(e.target.value)}
            placeholder="Describe your project requirements in detail. Include:&#10;- What problem does it solve?&#10;- Key features and functionality&#10;- Target users&#10;- Technical constraints&#10;- Non-functional requirements (performance, security, etc.)"
            rows={12}
            className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent font-mono text-sm resize-y"
            required
          />
          <p className="text-xs text-gray-500 mt-2">
            Supports Markdown formatting. Be as detailed as possible for better results.
          </p>
        </div>

        {/* File Upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Attachments (Optional)
          </label>
          <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center hover:border-gray-300 transition-colors">
            <input
              type="file"
              id="fileUpload"
              multiple
              onChange={handleFileUpload}
              className="hidden"
              accept=".md,.txt,.doc,.docx,.pdf"
            />
            <label htmlFor="fileUpload" className="cursor-pointer">
              <Upload className="h-8 w-8 mx-auto text-gray-400 mb-2" />
              <p className="text-sm text-gray-500">
                Drop files here or click to upload
              </p>
              <p className="text-xs text-gray-400 mt-1">
                Supports .md, .txt, .doc, .docx, .pdf
              </p>
            </label>
          </div>

          {/* Uploaded files list */}
          {uploadedFiles.length > 0 && (
            <div className="mt-3 space-y-2">
              {uploadedFiles.map((file, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between px-3 py-2 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-700">{file.name}</span>
                    <span className="text-xs text-gray-400">
                      ({Math.round(file.size / 1024)}KB)
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleRemoveFile(index)}
                    className="p-1 hover:bg-gray-200 rounded transition-colors"
                  >
                    <X className="h-4 w-4 text-gray-400" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-between pt-4">
          <div className="text-sm text-gray-500">
            <span className="flex items-center gap-1">
              <CheckCircle className="h-4 w-4 text-green-500" />
              All data is processed securely
            </span>
          </div>
          <button
            type="submit"
            disabled={isSubmitting || !projectName.trim() || !requirements.trim()}
            className={clsx(
              'flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-all',
              isSubmitting || !projectName.trim() || !requirements.trim()
                ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                : 'bg-primary-500 text-white hover:bg-primary-600 shadow-sm hover:shadow'
            )}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Creating...
              </>
            ) : (
              <>
                <Send className="h-4 w-4" />
                Create Project
              </>
            )}
          </button>
        </div>
      </motion.form>

      {/* Info section */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-8 p-4 bg-blue-50 rounded-lg border border-blue-100"
      >
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-700">
            <p className="font-medium mb-1">What happens next?</p>
            <ul className="space-y-1 text-blue-600">
              <li>1. Requirement Analyzer will extract and structure your requirements</li>
              <li>2. Architect Agent will design the system architecture</li>
              <li>3. Stack Recommender will suggest optimal technologies</li>
              <li>4. Document Agent will generate comprehensive documentation</li>
            </ul>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

export default RequirementInput;
