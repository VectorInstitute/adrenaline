import React, { useState, useCallback } from 'react';
import TextareaAutosize from 'react-textarea-autosize';
import { Flex, Button, Text, Switch, useColorModeValue } from '@chakra-ui/react';
import { ArrowUpIcon } from '@chakra-ui/icons';

interface SearchBoxProps {
  onSearch: (query: string, isPatientMode: boolean) => void;
  isLoading: boolean;
  isPatientPage?: boolean;
}

const SearchBox: React.FC<SearchBoxProps> = ({ onSearch, isLoading, isPatientPage = false }) => {
  const [query, setQuery] = useState<string>('');
  const [isPatientMode, setIsPatientMode] = useState<boolean>(isPatientPage);

  const handleQueryChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuery(e.target.value);
  }, []);

  const handleSearch = useCallback(() => {
    if (query.trim()) {
      onSearch(query.trim(), isPatientMode);
    }
  }, [query, onSearch, isPatientMode]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  }, [handleSearch]);

  const toggleMode = useCallback(() => {
    setIsPatientMode(prev => !prev);
  }, []);

  const bgColor = useColorModeValue('white', 'gray.800');
  const buttonBgColor = useColorModeValue('#1f5280', '#3a7ab3');
  const patientTextColor = isPatientMode ? buttonBgColor : 'black';

  return (
    <Flex direction="column" align="center" w="100%" maxW="600px" my={4}>
      <Flex
        w="100%"
        position="relative"
        align="center"
        border="2px solid"
        borderColor="gray.200"
        borderRadius="md"
        overflow="hidden"
      >
        <TextareaAutosize
          value={query}
          onChange={handleQueryChange}
          onKeyPress={handleKeyPress}
          placeholder={isPatientPage ? "Ask a question about this patient..." : (isPatientMode ? "Enter patient ID" : "Ask a question...")}
          minRows={3}
          maxRows={10}
          style={{
            width: '100%',
            resize: 'none',
            border: 'none',
            outline: 'none',
            padding: '12px 100px 12px 16px',
            backgroundColor: bgColor,
            color: 'inherit',
            fontSize: '16px',
            lineHeight: '1.5',
            maxRows: '300px',
            overflowY: 'auto',
          }}
        />
        <Flex position="absolute" right={2} top="75%" transform="translateY(-50%)" align="center">
          {!isPatientPage && (
            <>
              <Switch
                size="md"
                isChecked={isPatientMode}
                onChange={toggleMode}
                mr={2}
              />
              <Text fontSize="xs" fontWeight="medium" color={patientTextColor} mr={2}>
                Patient
              </Text>
            </>
          )}
          <Button
            size="sm"
            colorScheme="blue"
            isLoading={isLoading}
            onClick={handleSearch}
            bg={buttonBgColor}
            p={2}
            minW="auto"
          >
            <ArrowUpIcon />
          </Button>
        </Flex>
      </Flex>
    </Flex>
  );
};

export default SearchBox;
