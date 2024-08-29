import React, { useMemo, useCallback } from 'react';
import { Box, Text, Popover, PopoverTrigger, PopoverContent, PopoverBody, PopoverArrow, useColorModeValue } from '@chakra-ui/react';

interface Entity {
  entity_group: string;
  word: string;
  start: number;
  end: number;
  score: number;
}

interface EntityVisualizationProps {
  text: string;
  entities: Entity[];
}

const EntityVisualization: React.FC<EntityVisualizationProps> = ({ text, entities }) => {
  const sortedEntities = useMemo(() => [...entities].sort((a, b) => a.start - b.start), [entities]);
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');

  const getEntityColor = useCallback((entityGroup: string) => {
    const baseColors = [
      'red', 'blue', 'green', 'yellow', 'purple', 'orange', 'pink', 'teal', 'cyan', 'gray'
    ];

    const hash = entityGroup.split('').reduce((acc, char) => char.charCodeAt(0) + acc, 0);
    const colorIndex = hash % baseColors.length;
    const shade = (hash % 3 + 1) * 100; // This will give us shades 100, 200, or 300

    return `${baseColors[colorIndex]}.${shade}`;
  }, []);

  const renderText = useCallback(() => {
    let lastIndex = 0;
    const elements = [];

    sortedEntities.forEach((entity, index) => {
      if (entity.start > lastIndex) {
        elements.push(
          <Text as="span" key={`text-${index}`}>
            {text.slice(lastIndex, entity.start)}
          </Text>
        );
      }

      elements.push(
        <Popover key={`entity-${index}`} trigger="hover" placement="top">
          <PopoverTrigger>
            <Text
              as="span"
              bg={getEntityColor(entity.entity_group)}
              px={1}
              borderRadius="sm"
              cursor="pointer"
            >
              {text.slice(entity.start, entity.end)}
            </Text>
          </PopoverTrigger>
          <PopoverContent bg={bgColor} borderColor={borderColor}>
            <PopoverArrow />
            <PopoverBody>
              <strong>Entity:</strong> {entity.entity_group}<br />
              <strong>Word:</strong> {entity.word}<br />
              <strong>Score:</strong> {entity.score.toFixed(2)}
            </PopoverBody>
          </PopoverContent>
        </Popover>
      );

      lastIndex = entity.end;
    });

    if (lastIndex < text.length) {
      elements.push(
        <Text as="span" key="text-last">
          {text.slice(lastIndex)}
        </Text>
      );
    }

    return elements;
  }, [text, sortedEntities, getEntityColor, bgColor, borderColor]);

  return (
    <Box whiteSpace="pre-wrap">
      {renderText()}
    </Box>
  );
};

export default React.memo(EntityVisualization);
