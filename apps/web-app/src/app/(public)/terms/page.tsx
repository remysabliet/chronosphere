import { Card, CardContent } from '@/ui/card'
import { Separator } from '@/ui/separator'

export const metadata = {
  title: 'Terms of Service - Memosphere',
  description: 'Terms of Service for using the Memosphere platform.',
}

export default function TermsPage() {
  return (
    <div className="py-24 sm:py-32">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <header className="mb-12">
            <h1 className="heading-1 mb-4">Terms of Service</h1>
            <p className="text-muted-foreground">
              Last updated: {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
            </p>
          </header>

          <Card>
            <CardContent className="prose prose-gray dark:prose-invert max-w-none pt-6">
              <section aria-labelledby="acceptance">
                <h2 id="acceptance">1. Acceptance of Terms</h2>
                <p>
                  By accessing and using Memosphere ("Service"), you accept and agree to be bound by the terms and provision of this agreement. If you do not agree to these Terms of Service, please do not use the Service.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="description">
                <h2 id="description">2. Description of Service</h2>
                <p>
                  Memosphere provides an AI-powered adaptive learning platform that includes:
                </p>
                <ul>
                  <li>Personalized quiz sessions with adaptive difficulty</li>
                  <li>Multimedia memocards with spaced repetition</li>
                  <li>Learning analytics and progress tracking</li>
                  <li>Content creation and management tools</li>
                </ul>
                <p>
                  The Service may change from time to time, at our sole discretion, and without notice.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="registration">
                <h2 id="registration">3. User Registration</h2>
                <p>
                  To access certain features of the Service, you must register for an account. When you register, you agree to:
                </p>
                <ul>
                  <li>Provide accurate, current, and complete information</li>
                  <li>Maintain and update your information to keep it accurate and current</li>
                  <li>Maintain the security of your password and account</li>
                  <li>Accept all responsibility for activities that occur under your account</li>
                  <li>Notify us immediately of any unauthorized use of your account</li>
                </ul>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="conduct">
                <h2 id="conduct">4. User Conduct</h2>
                <p>
                  You agree not to use the Service to:
                </p>
                <ul>
                  <li>Upload, post, or transmit any content that is unlawful, harmful, threatening, abusive, harassing, defamatory, vulgar, obscene, or otherwise objectionable</li>
                  <li>Impersonate any person or entity or falsely state or misrepresent your affiliation with a person or entity</li>
                  <li>Interfere with or disrupt the Service or servers or networks connected to the Service</li>
                  <li>Attempt to gain unauthorized access to any portion of the Service or any other systems or networks</li>
                  <li>Use any robot, spider, scraper, or other automated means to access the Service</li>
                  <li>Reverse engineer, decompile, or disassemble any aspect of the Service</li>
                </ul>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="content">
                <h2 id="content">5. User Content</h2>
                <p>
                  You retain all rights to any content you submit, post, or display on or through the Service ("User Content"). By submitting User Content, you grant us a worldwide, non-exclusive, royalty-free license to use, copy, reproduce, process, adapt, modify, publish, transmit, display, and distribute such content.
                </p>
                <p>
                  You are solely responsible for your User Content and the consequences of posting or publishing it. You represent and warrant that:
                </p>
                <ul>
                  <li>You own or have the necessary licenses, rights, consents, and permissions to use and authorize us to use all User Content</li>
                  <li>Your User Content does not violate any applicable law or infringe any third party's rights</li>
                </ul>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="intellectual-property">
                <h2 id="intellectual-property">6. Intellectual Property</h2>
                <p>
                  The Service and its original content (excluding User Content), features, and functionality are owned by Memosphere and are protected by international copyright, trademark, patent, trade secret, and other intellectual property laws.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="subscriptions">
                <h2 id="subscriptions">7. Subscriptions and Payments</h2>
                <p>
                  Some parts of the Service are billed on a subscription basis ("Subscription"). You will be billed in advance on a recurring and periodic basis ("Billing Cycle"). Billing cycles are set on a monthly or annual basis.
                </p>
                <p>
                  A valid payment method is required to process the payment for your Subscription. You agree to provide current, complete, and accurate purchase and account information.
                </p>
                <p>
                  Subscriptions automatically renew unless cancelled before the renewal date. You may cancel your Subscription at any time through your account settings.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="refunds">
                <h2 id="refunds">8. Refunds</h2>
                <p>
                  We offer a 14-day money-back guarantee for paid subscriptions. If you're not satisfied with the Service, you may request a full refund within 14 days of your initial purchase.
                </p>
                <p>
                  Refund requests after 14 days will be evaluated on a case-by-case basis. Recurring subscription payments are non-refundable except as required by law.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="termination">
                <h2 id="termination">9. Termination</h2>
                <p>
                  We may terminate or suspend your account and access to the Service immediately, without prior notice or liability, for any reason, including if you breach the Terms.
                </p>
                <p>
                  Upon termination, your right to use the Service will immediately cease. All provisions of the Terms which by their nature should survive termination shall survive, including ownership provisions, warranty disclaimers, and limitations of liability.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="disclaimer">
                <h2 id="disclaimer">10. Disclaimer of Warranties</h2>
                <p>
                  THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND, EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT.
                </p>
                <p>
                  We do not warrant that the Service will be uninterrupted, timely, secure, or error-free, or that defects will be corrected.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="limitation">
                <h2 id="limitation">11. Limitation of Liability</h2>
                <p>
                  IN NO EVENT SHALL MEMOSPHERE, ITS DIRECTORS, EMPLOYEES, PARTNERS, AGENTS, SUPPLIERS, OR AFFILIATES BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR PUNITIVE DAMAGES, INCLUDING LOSS OF PROFITS, DATA, USE, OR OTHER INTANGIBLE LOSSES, RESULTING FROM YOUR ACCESS TO OR USE OF OR INABILITY TO ACCESS OR USE THE SERVICE.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="governing-law">
                <h2 id="governing-law">12. Governing Law</h2>
                <p>
                  These Terms shall be governed by and construed in accordance with the laws of the jurisdiction in which Memosphere operates, without regard to its conflict of law provisions.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="changes">
                <h2 id="changes">13. Changes to Terms</h2>
                <p>
                  We reserve the right to modify or replace these Terms at any time. If a revision is material, we will provide at least 30 days' notice prior to any new terms taking effect.
                </p>
                <p>
                  By continuing to access or use our Service after revisions become effective, you agree to be bound by the revised terms.
                </p>
              </section>

              <Separator className="my-8" />

              <section aria-labelledby="contact">
                <h2 id="contact">14. Contact Us</h2>
                <p>
                  If you have any questions about these Terms, please contact us at:
                </p>
                <p>
                  <strong>Email:</strong> legal@memosphere.com<br />
                  <strong>Website:</strong> <a href="https://memosphere.com">https://memosphere.com</a>
                </p>
              </section>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
