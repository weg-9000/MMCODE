/**
 * AnalysisBlockNode component
 * Displays requirement analysis results in block format
 */

import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { FileSearch, CheckCircle2, AlertCircle, Users, Target } from 'lucide-react';
import { BaseBlockNode } from './BaseBlockNode';
import { TechStackBadge } from '../shared/TechStackBadge';
import type { AnalysisBlockSummary } from '@/types';

/**
 * Props extending BlockNodeData with analysis-specific data
 */
interface AnalysisNodeData extends AnalysisBlockSummary {
  title: string;
  type: 'analysis';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  qualityScore?: number;
}

/**
 * AnalysisBlockNode - Displays requirement analysis
 */
export const AnalysisBlockNode = memo(function AnalysisBlockNode(
  props: NodeProps<AnalysisNodeData>
) {
  const { data } = props;
  const {
    functionalRequirements = [],
    nonFunctionalRequirements = [],
    domainConcepts = [],
    stakeholders = [],
  } = data;

  return (
    <BaseBlockNode
      {...props}
      icon={<FileSearch className="h-4 w-4 text-purple-600" />}
      headerColor="bg-purple-50"
    >
      <div className="space-y-3">
        {/* Functional Requirements */}
        <div>
          <div className="flex items-center gap-1.5 mb-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-purple-500" />
            <span className="text-xs font-medium text-gray-700">
              Functional ({functionalRequirements.length})
            </span>
          </div>
          <div className="flex flex-wrap gap-1">
            {functionalRequirements.slice(0, 4).map((req, idx) => (
              <span
                key={idx}
                className="px-2 py-0.5 text-xs bg-purple-50 text-purple-700 rounded-full border border-purple-200"
              >
                {typeof req === 'string' ? req : req.name}
              </span>
            ))}
            {functionalRequirements.length > 4 && (
              <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">
                +{functionalRequirements.length - 4}
              </span>
            )}
          </div>
        </div>

        {/* Non-Functional Requirements */}
        {nonFunctionalRequirements.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <AlertCircle className="h-3.5 w-3.5 text-orange-500" />
              <span className="text-xs font-medium text-gray-700">
                Non-Functional ({nonFunctionalRequirements.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {nonFunctionalRequirements.slice(0, 3).map((req, idx) => (
                <span
                  key={idx}
                  className="px-2 py-0.5 text-xs bg-orange-50 text-orange-700 rounded-full border border-orange-200"
                >
                  {typeof req === 'string' ? req : req.category}
                </span>
              ))}
              {nonFunctionalRequirements.length > 3 && (
                <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">
                  +{nonFunctionalRequirements.length - 3}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Domain Concepts */}
        {domainConcepts.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Target className="h-3.5 w-3.5 text-blue-500" />
              <span className="text-xs font-medium text-gray-700">
                Domain Concepts ({domainConcepts.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {domainConcepts.slice(0, 4).map((concept, idx) => (
                <TechStackBadge
                  key={idx}
                  name={typeof concept === 'string' ? concept : concept.name}
                  category="framework"
                  size="sm"
                />
              ))}
            </div>
          </div>
        )}

        {/* Stakeholders */}
        {stakeholders.length > 0 && (
          <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
            <Users className="h-3.5 w-3.5 text-gray-400" />
            <span className="text-xs text-gray-500">
              {stakeholders.length} stakeholder{stakeholders.length !== 1 ? 's' : ''}
            </span>
          </div>
        )}
      </div>
    </BaseBlockNode>
  );
});

export default AnalysisBlockNode;
