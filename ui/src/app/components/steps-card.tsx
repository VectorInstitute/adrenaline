import React from 'react';
import { Box, Text, VStack, useColorModeValue } from '@chakra-ui/react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckIcon } from '@chakra-ui/icons';

interface Step {
  step: string;
  reasoning: string;
}

interface StepsCardProps {
  steps: Step[];
}

const StepsCard: React.FC<StepsCardProps> = ({ steps }) => {
  const bgColor = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('blue.100', 'blue.700');
  const headerBgColor = useColorModeValue('blue.50', 'blue.900');

  return (
    <Box
      bg={bgColor}
      borderWidth={2}
      borderColor={borderColor}
      borderRadius="md"
      overflow="hidden"
      shadow="lg"
    >
      <Box bg={headerBgColor} p={4}>
        <Text fontWeight="bold" fontSize="lg" fontFamily="'Roboto Slab', serif">Reasoning Steps</Text>
      </Box>
      <VStack align="stretch" spacing={4} p={4}>
        <AnimatePresence>
          {steps.map((stepObj, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
            >
              <Box display="flex" alignItems="center">
                <Box color="green.500" mr={2}>
                  <CheckIcon />
                </Box>
                <Text fontWeight="bold" color="blue.500" fontFamily="'Roboto Slab', serif">Step {index + 1}: {stepObj.step}</Text>
              </Box>
              <Text mt={1} fontFamily="'Roboto Slab', serif">{stepObj.reasoning}</Text>
            </motion.div>
          ))}
        </AnimatePresence>
      </VStack>
    </Box>
  );
};

export default StepsCard;
