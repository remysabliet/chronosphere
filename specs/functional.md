# Scope 1: Minimum Viable Product (MVP) - Functional Requirements

## Core Features

### User Authentication
- **Feature**: Enable users to create accounts, log in, and manage their profiles.
- **Details**: Utilize authentication frameworks like Auth0 or implement custom authentication with JWT for security.

### Data Input and Validation
- **Feature**: Users can input text via a text area or document upload.
- **Validation Option**: Include optional validation checks for spelling, grammar, and factual accuracy using predefined data standards or trusted sources.

### AI-Driven Question Generation
- **Details**: Use a backend system integrated with ChatGPT or a similar language model to dynamically generate quizzes based on user performance and track metrics.

- **Leverage embedding for question retrieval (CF) Additional feature**

### Interactive Learning Sessions
- **Sessions**: Enable interactive sessions where users respond to questions.
- **Timed Sessions**: Include optional timed sessions to simulate testing conditions.

### Analysis of User Responses
- **Tracking Answers**: Systematically record answers to identify learning patterns.
- **Performance Metrics**: Calculate and provide feedback on user performance metrics.

### Adaptive Learning Algorithms
- **Weak Area Identification**: Algorithms identify and target the user’s weak areas.
- **Focused Questioning**: Dynamically generate content focused on these areas.
- **Progressive Difficulty**: Adjust question difficulty based on performance.

### Reporting and Analytics
- **User Progress Reports**: Detailed visual analytics on user progress and areas for improvement.
- **Session Summaries**: Summarize performance and time spent after each session.

### User Profile and History
- **Profile Management**: Allow users to manage personal and educational profiles.
- **Learning History**: Maintain logs of all interactions, sessions, and progress.

### Content Management System (CMS)
- **Admin Tools**: Facilities for admins to manage question content.
- **Content Tagging and Categorization**: Tag and categorize content to streamline management and retrieval.

## Types of Questions

### Multiple Choice Questions (MCQs)
- **Details**: Generate questions with multiple answers; one correct. Options for 3, 4, or 5 choices.

### True/False Questions
- **Details**: Based on statements from the text, users judge truthfulness.

### Fill-in-the-Blanks
- **Details**: Users fill in missing words in provided sentences.

### Short Answer
- **Details**: Open-ended questions requiring brief responses.

### Memo Cards (Flashcards)
- **Details**: Questions and answers on flashcards for self-testing.

### Matching Questions
- **Details**: Users match terms to definitions or categories.

### Sequential Order Questions
- **Details**: Arrange events or processes in the correct sequence from the content.

## Additional Features for Embeddings

### Efficiency and Personalization
- **Embedding Utilization**: Use pre-trained models like Sentence-BERT for generating embeddings of question text for efficient retrieval and matching.
- **Dynamic Retrieval**: Quickly find semantically related questions based on user learning patterns and weaknesses.

### System Scalability and Maintenance
- **Storage Considerations**: Plan for increased storage needs due to vector storage of embeddings.
- **Model Updates**: Regularly update and refine the embedding model as more data is collected to improve performance and relevance.

### AI Algorithms Integration
- **Clustering and Matching**: Utilize clustering or nearest neighbor algorithms to identify groups of questions for targeted learning.

## Additional Considerations

### Accessibility and Compliance
- **Accessibility**: Ensure the platform complies with WCAG guidelines.
- **Security and Privacy**: Implement robust measures to protect user data and privacy.
