import { Card, CardContent } from '@/ui/card'
import { Separator } from '@/ui/separator'

export const metadata = {
  title: 'Privacy Policy - Memosphere',
  description: 'Privacy Policy for Memosphere. Learn how we collect, use, and protect your data.',
}

export default function PrivacyPage() {
  return (
    <div className="py-24 sm:py-32">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <header className="mb-12">
            <h1 className="heading-1 mb-4">Privacy Policy</h1>
            <p className="text-muted-foreground">
              Last updated: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </header>

          <Card>
            <CardContent className="prose prose-gray dark:prose-invert max-w-none pt-6">
              <section aria-labelledby="introduction">
                <h2 id="introduction">1. Introduction</h2>
                <p>
                  Memosphere ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our Service.
                </p>
                <p>
                  By using the Service, you agree to the collection and use of information in accordance with this policy. If you do not agree with our policies and practices, please do not use the Service.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="information-collection">
                <h2 id="information-collection">2. Information We Collect</h2>

                <h3>2.1 Information You Provide</h3>
                <p>
                  We collect information that you voluntarily provide when you:
                </p>
                <ul>
                  <li>Register for an account (name, email address, password)</li>
                  <li>Create learning content (decks, cards, questions)</li>
                  <li>Use our learning features (quiz responses, study sessions)</li>
                  <li>Contact our support team (messages, feedback)</li>
                  <li>Subscribe to our newsletter or promotional emails</li>
                </ul>

                <h3>2.2 Automatically Collected Information</h3>
                <p>
                  When you use the Service, we automatically collect:
                </p>
                <ul>
                  <li><strong>Usage Data:</strong> Pages visited, features used, time spent, interactions</li>
                  <li><strong>Device Information:</strong> IP address, browser type, operating system, device identifiers</li>
                  <li><strong>Learning Data:</strong> Performance metrics, quiz scores, retention rates, study patterns</li>
                  <li><strong>Cookies and Tracking:</strong> Session tokens, preferences, analytics data</li>
                </ul>

                <h3>2.3 Third-Party Information</h3>
                <p>
                  If you sign in through OAuth providers (Google, GitHub, etc.), we receive basic profile information as permitted by your settings with that provider.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="how-we-use">
                <h2 id="how-we-use">3. How We Use Your Information</h2>
                <p>
                  We use the information we collect to:
                </p>
                <ul>
                  <li><strong>Provide the Service:</strong> Create and manage your account, deliver learning features</li>
                  <li><strong>Personalize Experience:</strong> Adapt content difficulty, optimize spaced repetition, provide analytics</li>
                  <li><strong>Improve the Service:</strong> Analyze usage patterns, develop new features, fix bugs</li>
                  <li><strong>Communicate:</strong> Send account notifications, updates, marketing communications (with consent)</li>
                  <li><strong>Security:</strong> Detect fraud, prevent abuse, protect user accounts</li>
                  <li><strong>Comply with Legal Obligations:</strong> Respond to legal requests, enforce our terms</li>
                </ul>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="legal-basis">
                <h2 id="legal-basis">4. Legal Basis for Processing (GDPR)</h2>
                <p>
                  For users in the European Economic Area (EEA), we process your personal data under the following legal bases:
                </p>
                <ul>
                  <li><strong>Contract Performance:</strong> Processing necessary to provide the Service</li>
                  <li><strong>Legitimate Interests:</strong> Improving the Service, security, fraud prevention</li>
                  <li><strong>Consent:</strong> Marketing communications, optional data collection</li>
                  <li><strong>Legal Obligations:</strong> Compliance with applicable laws</li>
                </ul>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="data-sharing">
                <h2 id="data-sharing">5. How We Share Your Information</h2>
                <p>
                  We do not sell your personal information. We may share your information with:
                </p>
                <ul>
                  <li><strong>Service Providers:</strong> Cloud hosting (AWS), analytics (Google Analytics), payment processing (Stripe), email services (SendGrid)</li>
                  <li><strong>Authentication Providers:</strong> AWS Cognito, OAuth providers (Google, GitHub) for login</li>
                  <li><strong>Legal Requirements:</strong> Law enforcement, regulatory authorities when legally required</li>
                  <li><strong>Business Transfers:</strong> In connection with merger, acquisition, or sale of assets</li>
                  <li><strong>With Your Consent:</strong> When you explicitly authorize sharing (e.g., collaborative learning features)</li>
                </ul>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="data-security">
                <h2 id="data-security">6. Data Security</h2>
                <p>
                  We implement appropriate technical and organizational measures to protect your data:
                </p>
                <ul>
                  <li><strong>Encryption:</strong> Data encrypted in transit (TLS/SSL) and at rest (AES-256)</li>
                  <li><strong>Access Controls:</strong> Role-based access, multi-factor authentication for staff</li>
                  <li><strong>Secure Infrastructure:</strong> AWS services with SOC 2 and ISO 27001 compliance</li>
                  <li><strong>Regular Audits:</strong> Security assessments, penetration testing, vulnerability scanning</li>
                </ul>
                <p>
                  However, no method of transmission over the Internet is 100% secure. We cannot guarantee absolute security.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="data-retention">
                <h2 id="data-retention">7. Data Retention</h2>
                <p>
                  We retain your personal information for as long as necessary to:
                </p>
                <ul>
                  <li>Provide the Service to you</li>
                  <li>Comply with legal obligations (e.g., tax records for 7 years)</li>
                  <li>Resolve disputes and enforce agreements</li>
                </ul>
                <p>
                  When you delete your account, we delete or anonymize your personal information within 90 days, except where retention is required by law.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="your-rights">
                <h2 id="your-rights">8. Your Privacy Rights</h2>
                <p>
                  Depending on your location, you may have the following rights:
                </p>
                <ul>
                  <li><strong>Access:</strong> Request a copy of your personal data</li>
                  <li><strong>Rectification:</strong> Correct inaccurate or incomplete data</li>
                  <li><strong>Erasure:</strong> Delete your personal data ("right to be forgotten")</li>
                  <li><strong>Portability:</strong> Receive your data in a machine-readable format</li>
                  <li><strong>Restriction:</strong> Limit how we process your data</li>
                  <li><strong>Objection:</strong> Object to processing based on legitimate interests</li>
                  <li><strong>Withdraw Consent:</strong> Opt out of marketing, withdraw consent for optional processing</li>
                </ul>
                <p>
                  To exercise these rights, contact us at <strong>privacy@memosphere.com</strong>. We will respond within 30 days.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="cookies">
                <h2 id="cookies">9. Cookies and Tracking Technologies</h2>
                <p>
                  We use cookies and similar tracking technologies to:
                </p>
                <ul>
                  <li><strong>Essential Cookies:</strong> Authentication, security, core functionality</li>
                  <li><strong>Analytics Cookies:</strong> Google Analytics to understand usage patterns</li>
                  <li><strong>Preference Cookies:</strong> Remember your settings and choices</li>
                </ul>
                <p>
                  You can control cookies through your browser settings. Note that disabling essential cookies may affect Service functionality.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="children">
                <h2 id="children">10. Children's Privacy</h2>
                <p>
                  Our Service is not intended for children under 13 years of age (or 16 in the EEA). We do not knowingly collect personal information from children.
                </p>
                <p>
                  If you are a parent or guardian and believe your child has provided us with personal information, please contact us. We will delete such information from our systems.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="international">
                <h2 id="international">11. International Data Transfers</h2>
                <p>
                  Your information may be transferred to and processed in countries other than your country of residence. These countries may have data protection laws different from your jurisdiction.
                </p>
                <p>
                  For EEA users, we use Standard Contractual Clauses approved by the European Commission to ensure adequate protection when transferring data outside the EEA.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="california">
                <h2 id="california">12. California Privacy Rights (CCPA)</h2>
                <p>
                  If you are a California resident, you have additional rights under the California Consumer Privacy Act (CCPA):
                </p>
                <ul>
                  <li><strong>Right to Know:</strong> What personal information we collect, use, and share</li>
                  <li><strong>Right to Delete:</strong> Request deletion of your personal information</li>
                  <li><strong>Right to Opt-Out:</strong> Opt out of the "sale" of personal information (we do not sell your data)</li>
                  <li><strong>Non-Discrimination:</strong> We will not discriminate against you for exercising your rights</li>
                </ul>
                <p>
                  To exercise these rights, email <strong>privacy@memosphere.com</strong> or call our toll-free number.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="changes">
                <h2 id="changes">13. Changes to This Policy</h2>
                <p>
                  We may update this Privacy Policy from time to time. We will notify you of material changes by:
                </p>
                <ul>
                  <li>Posting the new Privacy Policy on this page</li>
                  <li>Updating the "Last updated" date</li>
                  <li>Sending an email notification (for significant changes)</li>
                </ul>
                <p>
                  Your continued use of the Service after changes become effective constitutes acceptance of the revised policy.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="contact-privacy">
                <h2 id="contact-privacy">14. Contact Us</h2>
                <p>
                  If you have questions about this Privacy Policy or our data practices, please contact:
                </p>
                <p>
                  <strong>Data Protection Officer:</strong><br />
                  <strong>Email:</strong> privacy@memosphere.com<br />
                  <strong>Address:</strong> [Your Business Address]<br />
                  <strong>Phone:</strong> [Your Contact Number]
                </p>
                <p>
                  For EEA users, you also have the right to lodge a complaint with your local data protection authority.
                </p>
              </section>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
