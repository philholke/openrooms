My vision is to create a SevenRooms open-source clone - something that works >80% as well as SevenRooms, but without the unimportant fluff (all commercial SaaS will have some useless features that look flashy but ground ops never need/use).

To give us a solid lay of the land in terms of what 7R can currently do, I've prepared a detailed report overview:

# SevenRooms Product Blueprint: Complete Feature & Function Reference

## Executive Overview

SevenRooms is a cloud-based guest experience and retention platform for the hospitality industry, founded in 2011 by Joel Montaniel, Allison Page, and Kinesh Patel in New York City. It serves over 10,000 restaurants worldwide and was acquired by DoorDash for $1.2 billion in June 2025. The platform's core philosophy is **"Your Brand, Your Guest, Your Data"** — helping operators own their guest relationships rather than ceding them to third-party platforms like OpenTable or DoorDash.[1][2][3][4]

The platform is structured around three primary goals:
- **Acquire**: Drive commission-free reservations and orders directly through owned channels
- **Engage**: Operate front-of-house with data-rich tools that enable personalized service
- **Retain**: Use automated marketing to generate repeat business

SevenRooms positions itself as an all-in-one replacement for fragmented tech stacks — reservation software, waitlist app, CRM, email platform, loyalty system, reputation manager — consolidating everything into a single data layer.

***

## Pricing Tiers

SevenRooms uses a custom enterprise pricing model (no public per-seat pricing). Three tiers exist:[5]

| Tier | Key Features |
|------|-------------|
| **Essentials** | CRM & Guest Profiles, Unlimited Reservations, Reservation Upgrades & Offers, Standard Segmentations & Auto-tags, Waitlist, Table Management, Review Aggregation, Direct Feedback Surveys, Standard Automated Campaigns |
| **Growth** | Everything in Essentials + Multi-venue Reservations, Custom Segmentations & Auto-Tags, Events module, Custom Automated Campaigns |
| **Premium** | Everything in Growth + Custom User Permissions, Group Reporting, Group Segmentation |

**Add-ons** (not bundled in base tiers): Email Marketing, Text/SMS Marketing.[6]

Starting price is approximately $499–$700/month per venue with custom enterprise quotes for multi-location groups. The platform uses annual contracts with no per-cover fees on direct bookings.[7][8]

***

## Module 1: Reservations & Waitlist

This is the core engine of the platform — the public-facing booking system through which guests discover and book tables.

### 1.1 Online Booking Widget

The reservation widget is the guest-facing entry point and embeds directly on the restaurant's own website and social channels.[9]

- **White-label, fully brandable** widget — operators control colors, fonts, logo, and copy[9]
- Supports **14 languages** for international venues[10]
- Embedded via JavaScript (`SevenroomsWidget.init()`) with `venueId`, `type`, and `triggerId` parameters[11]
- Widget types: `reservations`, `waitlist`, `events`
- Customizable guest-facing messaging, policies, and confirmation emails[6]
- Widget captures data fields: name, email, phone, party size, date/time, special requests, dietary restrictions, birthdays, and more
- Optional social login to pull additional profile data (name, birthday, job title)[9]

### 1.2 Booking Channels & Discovery

SevenRooms plugs into third-party discovery channels while keeping bookings commission-free for operators:[10]

- **Google** (Search, Maps, Google Assistant, Reserve with Google)
- **Facebook** (Book Now CTA button)
- **Instagram** (Reserve action button, integrated since October 2018)[2]
- **TheFork** (European market)
- **Yelp** (via Call to Action booking button)
- **TripAdvisor** (linked booking)
- The platform uses **unique tracking links** per channel to measure which source drives bookings[12]

### 1.3 Access Rules & Availability Scheduling

Access Rules are the configuration layer that defines when, who, and how guests can book:[13]

- Create multiple named availability rules per venue
- Set rules by: day of week, date range, meal period (lunch/dinner/brunch)
- Define **party size ranges** per rule
- Define **time slots** and **slot intervals** (e.g., every 15/30/60 minutes)
- Set **max covers per slot** (pacing)
- Control **how far in advance** guests can book (e.g., up to 28 days, 60 days)
- Set **cut-off times** (e.g., no bookings within 2 hours of service)
- Assign rules to specific **seating areas** (e.g., bar, patio, private dining room)
- **Custom Audiences**: control which booking sources or member groups can access specific rules (e.g., Peoplevine members, hotel guests, public)[13]
- **Time Slot Descriptions**: add public descriptions shown in booking flow
- Rules support exclusions for holidays, special event dates

### 1.4 No-Shows, Deposits & Cancellation Policies

SevenRooms provides multiple mechanisms to protect against revenue loss from no-shows:[14][15]

- **Credit card hold**: store card without charging at time of booking
- **Partial deposit**: charge a fixed amount or per-person amount upfront
- **Full prepayment**: charge total bill (common for tasting menus)
- **No-show fee**: automatically charge stored card if guest doesn't arrive
- **Cancellation fee**: charge if cancellation is within a defined window (e.g., <24 hours or <48 hours)
- Operators define the policy window and amount per access rule
- Average U.S. cancellation fee is $52[14]
- Example: one operator reduced no-show rate from 15% to 1% after implementing deposits[14]
- Guests are shown the cancellation policy during booking and must agree
- SevenRooms acts as payment facilitator (via Stripe and other gateways); collects a processing fee where applicable[15]
- PCI-compliant card capture and secure storage[16]

### 1.5 Priority Alerts & Waitlist Availability

When a cancellation occurs, SevenRooms can automatically notify specific guest segments rather than blasting the entire waitlist:[17]

- Operator defines **priority tiers**: VIPs first, then loyalty members, then regulars, then general waitlist
- Guests on priority list receive an SMS/email alert with a direct link to claim the slot
- First to respond gets the reservation; slot returns to pool if not taken within a time limit
- Replaces indiscriminate OpenTable-style cancellation blasts with targeted, VIP-first distribution

### 1.6 Virtual Waitlist

For walk-ins and real-time seating:[18][19]

- Guests join via: QR code scan at entrance, text to a number, Google Reserve, operator-added at host stand
- Real-time wait time estimation (synced with actual floor plan state)
- SMS updates as position in queue changes
- Guest self-check-in via SMS link when near the top of list
- Multi-venue waitlist: guests can see wait times across all locations in a group and choose preferred venue[19]
- Walk-outs: if a guest leaves the waitlist before being seated, automated win-back email/SMS is triggered[19]
- Two-way SMS: guests can text to say they're running late

### 1.7 WhatsApp Messaging (EMEA & APAC)

- Automated reservation confirmations and reminders via WhatsApp[10]
- Real-time waitlist and reservation status updates
- Available in Europe, Middle East, Africa, and Asia Pacific regions

### 1.8 Multi-Venue & Group Reservations

For hospitality groups and hotel chains:[20]

- Centralized guest database shared across all locations
- **Multi-location widget**: guests search availability across all portfolio properties from one interface
- **Cross-sell widget**: when a guest's preferred venue is full, alternative sister venues are surfaced automatically
- Reservation and table inventory shared in real time across properties
- User-level access permissions per venue (staff member can have different access at different sites)

***

## Module 2: Table Management

The host stand operating system — used on iPad tablets by front-of-house staff during service.

### 2.1 Interactive Floor Plan

- Fully customizable digital floor plan mapped to the physical venue layout[21]
- Multiple floor plan sections: indoor dining room, bar, patio, private dining, upstairs — toggled independently[21]
- Each table has: table number, capacity (min/max covers), shape, section
- **Drag-and-drop** table assignment: move reservations between tables
- Visual table states displayed with color coding (available, occupied, reserved, hold)
- Custom table statuses (e.g., "Last Round," "Needs Dessert")[22]
- **Label overlays**: switch view between guest name, party size, spend, table status, or turn time[21]
- **Real-time POS spend** per table shown live on floor plan (updates as orders are placed)[21]
- VIP and "hot reservation" tables get visual callout (highlighted border)

### 2.2 AI Auto-Seating Algorithm

- Evaluates **10,000+ seating combinations per second** to optimize table assignment[22]
- Considers: party size, table capacity, turn time, reservation timing, section balance, server workload
- Outputs optimal seating suggestions; host can override
- Claimed to increase table turns by up to 20%[12]

### 2.3 Reservation & Walk-in Operations

- View all reservations, walk-ins, and waitlisted parties in a single unified view
- Filter by meal period, section, server, or tag
- Add new reservations, walk-ins, or waitlist entries directly from the floor plan
- **Seat** a reservation: drag party to a table or tap-assign; triggers POS table open
- **Unseat**: close table, trigger check or note turn end time
- Mark reservation statuses: Confirmed, Arrived, Seated, Partially Arrived, No-Show, Cancelled, Left Message
- Add/edit reservation notes in real time
- Update party size on the fly
- **Combine tables** for large parties
- **Hold** a table for an arriving reservation

### 2.4 Pre-Shift Report

A feature introduced in 2023 that generates a briefing document before each service:[23][24]

- Automatically compiled from CRM and reservation data
- Accessible on iPhone, iPad, and on the host stand
- Shows all guests arriving in the upcoming shift with:
  - Name, party size, time
  - VIP status, tags (allergies, preferences, history)
  - Reservation notes and special requests
  - Past visit history and feedback scores
  - Spend history
- Grid view for shift-level planning and pacing visualization
- Day's notes on specials, private events, and kitchen alerts
- Distributed to all staff (GM, maître d', servers, BOH) before doors open
- Replaces paper print-outs and manual briefing prep

### 2.5 Server Assignment & Pacing

- Assign tables to specific servers
- Track server section and rotation
- View covers pacing per hour against targets
- Set turn time goals per meal period (e.g., 90-minute turns for dinner service)
- Turn time predictions appear on floor plan per table (estimated end time)

### 2.6 Real-Time Guest Alerts & SMS

- Push notifications to staff: new check-in, new reservation, cancellation, last-minute change
- **Centralized two-way SMS**: guests text the restaurant (via platform's SMS layer); all conversations centralized in the app[22]
- Staff can confirm reservation status, respond to "running late" messages
- Private Line VIP messaging (see Loyalty section)

### 2.7 Mobile App (SevenRooms OS)

- Native iOS/iPadOS app (App Store)[25]
- Requires iOS 17.6+ or iPadOS 17.6+
- Optimized for iPad (primary host stand device)
- iPhone version for floor-roaming managers
- Apple Watch app for quick glance features (table status, guest arrivals)[26]
- Android version available via mobile browser or Android-compatible app[27]
- All functionality mirrors web dashboard

***

## Module 3: CRM & Guest Profiles

The central data layer — every interaction across every module writes to this database.

### 3.1 Automated Profile Construction

Guest profiles are built automatically — no manual data entry required:[28]

- Profile is created or enriched at every touchpoint: reservation, walk-in, order, survey response, review
- **100+ unique data points** captured per guest
- Data captured includes:
  - Full name, email, phone number
  - Birthday, anniversary
  - Dietary restrictions and allergies
  - Dining preferences (cuisine type, seating preference, wine preferences)
  - Occasion types (work dinner, date night, birthday celebration)
  - Visit history (all locations, on and off-premise)
  - Order history (item-level via POS integration)
  - Lifetime spend (cumulative) and spend per visit
  - Feedback and review scores
  - Booking source (Google, Instagram, direct, third-party)
  - Social profile data (if social login used)
  - Staff notes from past visits

### 3.2 Tags & Auto-Tags

The tagging system is the segmentation engine powering both service personalization and marketing:[28]

- **Unlimited manual tags**: staff add tags like "Regular", "Corporate Account", "Influencer", "Complainer"
- **Auto-tags**: rules-based tags applied automatically when criteria are met
- Pre-built Auto-tag library with hospitality best practices
- Custom Auto-tags with rule builder (conditions: visit count, spend threshold, feedback score, booking source, date range, order items, etc.)
- Example Auto-tags:
  - `VIP` — spending above $X lifetime or X visits in Y days
  - `Steak Lover` — ordered steak 3+ times (POS data)
  - `Birthday This Week` — birthday within 7 days
  - `Lapsed 30 Days` — no visit in 30 days
  - `Positive Reviewer` — left 4-5 star feedback
  - `Negative Reviewer` — left 1-2 star feedback
  - `Third-Party Booker` — consistently books via OpenTable (target for direct conversion)
  - `First Timer` — first visit ever
  - `No Show` — marked no-show in last 90 days
  - `Big Spender` — top 10% by spend
  - `Regular` — visited 5+ times in last 6 months
- Auto-tags trigger automated emails/SMS campaigns
- Tags shared across venues in a portfolio (one profile, all locations)

### 3.3 Segmentation & Lookalike Audiences

- Filter the full guest database by any combination of tags, spend, visit date, location, booking channel, feedback score, etc.[28]
- Build named audience segments for marketing (e.g., "London VIPs who haven't visited in 60 days")
- Create **lookalike audiences**: find guests who share attributes with top spenders
- Export segments to CSV or push directly to email/SMS campaign
- Group-level segmentation (Premium tier): query across all venues in a portfolio simultaneously

### 3.4 Perks (In-Service Rewards)

A loyalty-adjacent feature for surprise-and-delight moments:[28]

- Operator defines a Perk (e.g., "Complimentary Glass of Champagne for Regulars")
- Perk is triggered by an Auto-tag when a matching guest is seated
- Alert appears on host/server's device: "Guest is a Regular — Perk: Send Champagne"
- No visible loyalty card or app required — invisible to the guest
- Used to reward loyalty without a formal points system

***

## Module 4: Marketing Automation

The trigger-based communication engine — runs campaigns automatically without manual execution.

### 4.1 Automated Email Campaigns (Pre-built)

Available out of the box in all tiers:[29][30]

| Campaign | Trigger | Goal |
|----------|---------|------|
| Reservation Confirmation | Reservation created | Confirm details, reduce no-shows |
| Pre-Arrival Reminder | X hours before reservation | Reduce no-shows, upsell |
| Order Confirmation | Online order placed | Reduce errors, provide receipt |
| Post-Visit Thank You | After reservation completed | Collect feedback, drive repeat |
| First-Timer Welcome | First visit tagged | Welcome, encourage return booking |
| Birthday Campaign | Birthday within X days | Drive birthday dinner booking |
| Anniversary Campaign | Anniversary date approaching | Drive special occasion booking |
| Win-Back (Lapsed) | No visit in 30/60/90 days | Re-engage lapsed guests |
| Positive Feedback Follow-up | 4-5 star survey response | Ask for public review, reinforce loyalty |
| Negative Feedback Follow-up | 1-2 star survey response | Service recovery, prevent public negative review |
| No-Show/Cancellation Win-back | No-show or late cancel | Invite back with incentive |
| Third-Party Booker Conversion | Booked via OTA 3+ times | Convert to direct booker |
| Big Spender Recognition | High-value spend Auto-tag | VIP acknowledgment, exclusive invite |
| Waitlist Left Win-back | Guest joined waitlist but left before seating | Recovery offer |
| Post-Event Follow-up | Attended a ticketed event | Feedback + next event promotion |
| Nurture Sequence | New subscriber or first order | Series of 3-5 emails over 30 days |

Custom automated campaigns (Growth and Premium tiers) allow operators to build their own triggers, timing, and content.[6]

### 4.2 Email Marketing (One-Time Campaigns)

Launched in March 2023 as a standalone email blast tool:[31]

- Send one-time campaigns to custom-defined audience segments
- **Visual drag-and-drop email editor** with full brand customization
- Pre-built hospitality templates (events, new menu, seasonal offer, holiday special)
- Audience selection: any CRM segment, Auto-tag, or manually built list
- **Revenue attribution**: each campaign tracks reservations, covers, and revenue generated back to the email[31]
- Performance metrics: open rate, click-through rate, unsubscribes, revenue per email sent
- No need for third-party ESP (Mailchimp, etc.) — built in-platform
- Supports fully custom HTML emails via editor or templates

### 4.3 Text / SMS Marketing (One-Time Campaigns)

Launched October 2024 via the acquisition of AI SMS platform HeyPluto:[32]

- Send one-time MMS campaigns
- **Unlimited character length** (unlike standard SMS 160-char limit)
- Support for emojis and multimedia attachments (event invites, happy hour menus, images)
- **15 hospitality-specific SMS templates** included
- Audience selection via CRM tags and segments
- Revenue tracking: reservations and spend linked back to specific SMS campaign
- Performance metrics per campaign
- Personalization fields (guest first name, last visit, etc.)

***

## Module 5: Events, Experiences & Add-Ons

Transforms the reservation booking flow into a revenue-generating experience sales engine.

### 5.1 Bookable Experiences

- Create named "Experiences" attached to the reservation flow (e.g., "Chef's Tasting Menu," "Wine Pairing," "Afternoon Tea")[33]
- Experiences can be restricted to: specific seating areas, specific time slots, specific party sizes
- Configurable as: included with reservation, optional upgrade, or mandatory prepay
- Full deposit or partial deposit collection at booking
- Guest selects experience during reservation process (no separate step required)
- Average venues generate $115K+ annually in prepaid experience revenue[33]

### 5.2 Reservation Add-Ons & Upsells

Items that can be added to any reservation during the booking flow:[33]

- Welcome drinks / bottles of wine
- Birthday/anniversary cake
- Floral arrangements
- Premium table location (window seat, private booth)
- Personalized menus
- Pre-ordered courses
- Each add-on has: name, image, description, price, and availability rules
- All add-on revenue is captured as prepaid revenue before the guest arrives
- Per-cover spend increase of 50% documented when prepayments are captured[33]

### 5.3 Ticketed Events

Full event management for turning the restaurant into an event venue:[33]

- Create ticketed events (cocktail classes, live music, drag bingo, bottomless brunch)
- Branded event landing page with all event details (description, photos, pricing)
- Ticket types: paid, free (guestlist), limited availability, tiered pricing
- Set inventory limits per ticket type
- Promote via email marketing, SMS, QR code, social media
- Revenue dashboard per event
- Distribute ticket invites to specific CRM segments (VIPs only, locals only, etc.)
- Events Widget embedded separately from reservations widget (same `type: "events"` parameter)
- Integration with **Tripleseat** for large private event/catering sales[34]

### 5.4 Booking Policies for Events

- Customizable cancellation windows and no-show fees per event
- Minimum spend policies for private dining or large groups
- Partial or full refund logic configured per event
- Automated reminder emails and SMS before event date

***

## Module 6: Online Ordering

Commission-free direct ordering for delivery, pickup, and on-site tableside.

### 6.1 Direct Delivery & Pickup

- Restaurant-branded ordering page (own domain or SevenRooms-hosted)[35]
- Orders placed via restaurant website, email links, or social media
- Zero commission — orders go direct, no third-party platform fee
- Order data (items, contact info, spend) stored in guest CRM profile
- Automated order confirmation email sent to guest
- Two-way integration with Deliverect to sync orders to POS and kitchen printer[36]
- Menu synced from POS via Deliverect integration
- Order status updates sent back to SevenRooms automatically[36]

### 6.2 Contactless Order & Pay (In-Venue)

BYOD (Bring Your Own Device) tableside ordering via QR code or NFC:[37]

- No app download required
- Guest scans QR code or taps NFC tag at table → opens digital menu in browser
- Guest selects items and pays via credit card or digital wallet (Apple Pay, Google Pay)
- Order goes to kitchen/POS
- Available access methods: QR code, NFC, direct URL
- In-service order history stored to guest CRM profile
- Useful for reducing labor costs and maintaining contactless service

***

## Module 7: Reputation Management

A centralized review aggregation and guest feedback management hub.

### 7.1 Post-Visit Feedback Surveys

- Automatically sent after dining/order/event via email[38]
- Captures: overall star rating, and specific ratings for food, drinks, service, ambiance
- Free-text comment field
- Timing controlled by operator (e.g., 2 hours after reservation end time)
- Survey responses linked to guest profile automatically
- Negative responses (1-2 stars) trigger win-back automation
- Positive responses (4-5 stars) prompt guest to post review on Google/Yelp/TripAdvisor

### 7.2 Review Aggregation Dashboard

- Connects to: **Google Reviews, Yelp, Facebook, TripAdvisor**[39]
- All reviews pulled into a single dashboard
- Daily digest email summary of new reviews
- Reply to reviews directly from SevenRooms dashboard (no need to log into each platform)
- Auto-tags applied based on review rating: `Positive Reviewer`, `Negative Reviewer`
- Link reviewer's profile to guest CRM record when email/name match is found
- View aggregate star rating per channel

***

## Module 8: Reporting & Analytics

### 8.1 Core Reports (30+ reports)[40][12]

**Reservation Reports:**
- Daily reservations snapshot (vs. historical)
- Covers by meal period, day, week, month
- Cancellation rate by venue and timeframe
- No-show rate by venue and timeframe
- Booking channel breakdown ("Booked By" report — tracks source: direct, Google, Facebook, OTA)
- Unique tracking link performance per channel
- Lead time report (how far in advance guests book)

**Guest Reports:**
- Guest database growth over time
- New vs. returning guest ratio
- Repeat visit percentage
- Average covers per guest
- Average spend per guest
- Spend patterns by segment or tag
- Lifetime value by guest cohort
- Guest segmentation breakdown (auto-tag distribution)

**Marketing Reports:**
- Email campaign performance (open rate, CTR, revenue attributed)
- Automated email performance per campaign type
- SMS campaign performance
- Conversion rate per campaign
- Revenue per email sent

**Operations Reports:**
- Server performance
- Table turn time
- Utilization by section/seating area
- Walk-in vs. reservation ratio
- Waitlist abandonment rate

### 8.2 Group/Portfolio Reporting (Premium tier)[20]

- Consolidated reporting across all venues in a group
- Drill down from group level to individual venue level
- Compare performance across locations
- Global search for any guest across all properties
- Group-level segmentation for cross-property campaigns

### 8.3 Scheduled & Exported Reports

- Filter any report and save as a named report
- Schedule recurring delivery (daily, weekly, monthly) to specified email addresses
- One-off report generation and export to CSV
- Reporting API available for integration with data warehouses (Snowflake, BigQuery, Redshift, PostgreSQL)[41]

***

## Module 9: Loyalty, VIP & Retention Features

A suite of non-traditional loyalty tools that prioritize behavioral data over points programs.

### 9.1 Priority Alerts

- When a reservation slot opens (cancellation), system identifies who to notify first[17]
- Operator defines priority tiers: e.g., VIPs → Loyalty Members → Regulars → General Waitlist
- System sends targeted SMS/email to highest-tier eligible guests first
- Guest who responds first claims the slot
- More granular than OpenTable/Resy's first-come-first-served cancellation alerts

### 9.2 Private Line

- Operators assign a private SMS number to specific high-value guests[17]
- VIPs, press, frequent diners, top spenders can text this number directly
- Conversations route into the SevenRooms mobile app inbox (centralized)
- Staff can action the request (book a table, add a special request, modify a reservation) directly from the message
- Positions the restaurant as offering concierge-level access to its best guests

### 9.3 Word-of-Mouth Referrals

- A unique referral link is auto-generated for every guest (pushed via post-visit survey and email campaigns)[42]
- Guest shares link with friends; when a friend makes a reservation, the referral is tracked
- Referring guest receives a configurable Perk reward (comp item, discount, loyalty points)
- Restaurant tracks referral volume and revenue attributed per source guest
- No separate loyalty app required — runs entirely through email/survey touch

### 9.4 Perks (In-Service)

- Pre-configured rewards triggered by CRM Auto-tags at the moment of seating[28]
- Examples: comp appetizer for VIP, champagne toast for anniversary, free dessert for 10th visit
- Alert appears on host/server device during check-in or seating
- Reward is documented in guest profile
- Used to create "invisible loyalty" — guest feels seen without knowing they're in a program

***

## Module 10: AI Features (2025)

Announced March 2025 as part of the "SuperHuman Hospitality™" initiative.[43][44]

### 10.1 AI Responses

- Automatically drafts personalized responses to guest emails, SMS messages, and online reviews
- Operator sets a "tone" preference (warm, professional, formal, casual) and AI maintains brand voice
- Staff review and send (not fully automated — human approval required)
- Impact: 27% reduction in time to respond; 35% more reviews responded to; 80% increase in messages sent within 2 minutes of starting a draft[45]

### 10.2 AI Feedback Summary

- Aggregates all guest feedback from all channels (surveys, Google, Yelp, Facebook, TripAdvisor)
- Generates a weekly summary highlighting themes, recurring praise, and recurring complaints
- Delivered as a concise actionable briefing
- Replaces manual review reading — operators get a full picture in seconds

### 10.3 AI Note Polish

- Automatically cleans, standardizes, and organizes unstructured guest notes entered by staff
- Transforms scattered, abbreviation-heavy notes into clear, readable profile entries
- Ensures the guest database stays clean and actionable as it scales

***

## Module 11: Integrations & Technical Architecture

### 11.1 POS Integrations (65+)[46][47][28]

Key verified integrations include:

| POS System | Notes |
|-----------|-------|
| Toast | Major US restaurant POS |
| Square for Restaurants | Direct bidirectional sync |
| Lightspeed O-Series | Customer data sync, item-level orders |
| Silverware | Enterprise hospitality POS |
| Eats365 | Asia-Pacific market POS |
| Redcat Polygon | Australian/NZ hospitality POS |

When POS is integrated:
- Guest is automatically created or matched in CRM on checkout
- Item-level order history attached to guest profile
- Real-time table spend visible on floor plan
- Table status auto-updates when POS check is opened/closed

### 11.2 Booking Channel Integrations

- Google Reserve (reservations and waitlist)
- Facebook / Instagram
- TheFork
- Yelp
- TripAdvisor

### 11.3 Communication Infrastructure

- **Twilio**: primary SMS gateway for all two-way SMS[47]
- WhatsApp Business API (EMEA/APAC)
- Native email delivery (no third-party ESP required)
- In-app push notifications (iOS/Android)

### 11.4 Payment Integrations

- **Stripe** (primary global processor)[16]
- Other regional processors supported via API
- PCI DSS compliant card storage
- Supports: credit cards, debit cards, Apple Pay, Google Pay
- Processing fee disclosed and collected separately from venue payment[15]

### 11.5 Other Integrations

- **Deliverect**: online ordering POS sync (two-way)[36]
- **Tripleseat**: private event/catering sales management[34]
- **Peoplevine**: membership management and access control[13]
- **PassKit**: Apple Wallet / Google Wallet pass generation (reservations, memberships, perks)[48]
- **Google Analytics**: booking widget event tracking (date selection, availability search, confirmation, promo code use)[49]
- **7shifts**: labor management integration[35]

### 11.6 Open API

- SevenRooms offers a documented open REST API[50]
- Used for: custom reporting pipelines, membership system integrations, loyalty program connections, data warehouse ETL
- API exposes: reservations, guest profiles, orders, feedback, availability
- Common ETL destinations: Snowflake, BigQuery, Amazon Redshift, PostgreSQL[41]
- API-based client token authentication for widget embedding

***

## Guest-Facing Journey (End-to-End)

Understanding the complete guest experience flow is essential for cloning the product:

1. **Discovery**: Guest finds restaurant on Google/Instagram/website
2. **Booking**: Guest opens widget; selects date, party size, time → browses available slots (filtered by Access Rules)
3. **Experience Selection**: Optional experiences or add-ons presented in booking flow
4. **Profile Data Capture**: Guest enters name, email, phone, dietary preferences, special occasion
5. **Payment**: Credit card hold, deposit, or full prepayment if required by Access Rule
6. **Confirmation**: Automated email sent immediately with reservation details and cancellation policy
7. **Pre-Visit Reminder**: Automated SMS/email 24-48 hours before reservation
8. **Arrival**: Host checks guest into floor plan; CRM profile surface on host device with tags/notes/history
9. **Seating**: AI auto-seating assigns table; Perks triggered if applicable
10. **In-Service**: Real-time POS spend tracks to floor plan; two-way SMS available
11. **Departure**: Automated post-visit feedback survey sent 1-2 hours after reservation end
12. **Follow-up**: Based on feedback score and Auto-tags, automated campaigns fire (thank you, win-back, review request, referral link)
13. **Re-engagement**: Lapsed guest triggers win-back campaign at 30/60/90 days

***

## Feature Comparison: SevenRooms vs. Key Competitors

| Feature | SevenRooms | OpenTable | Resy | Toast Tables |
|---------|-----------|-----------|------|-------------|
| Commission-free direct bookings | ✅ | ❌ (per-cover fee) | ❌ (per-cover fee) | ✅ |
| Operator owns guest data | ✅ | ❌ | ❌ | ✅ |
| Full CRM with 100+ data points | ✅ | ❌ | Partial | ❌ |
| Auto-tags & segmentation | ✅ | ❌ | ❌ | ❌ |
| Built-in email marketing | ✅ | ❌ | ❌ | ❌ |
| Built-in SMS marketing | ✅ | ❌ | ❌ | ❌ |
| AI auto-seating algorithm | ✅ | ❌ | ❌ | ❌ |
| Reputation management (review aggregation) | ✅ | Partial | ❌ | ❌ |
| Multi-venue group reporting | ✅ | Limited | ❌ | ✅ |
| Ticketed events & experiences | ✅ | ❌ | ❌ | ❌ |
| Commission-free online ordering | ✅ | ❌ | ❌ | ✅ |
| Open API | ✅ | ✅ | Limited | ✅ |
| 65+ POS integrations | ✅ | ✅ | Limited | ❌ (Toast only) |
| AI features (2025) | ✅ | ❌ | ❌ | ❌ |
| WhatsApp messaging | ✅ (EMEA/APAC) | ❌ | ❌ | ❌ |

***

## Architecture Notes for Cloning

Based on all available public technical information:

**Frontend:**
- Web dashboard (operator-facing): likely React/Next.js SPA
- Guest-facing widget: lightweight JavaScript embed (`embed.js`) with iframe or shadow DOM
- Mobile app: native iOS (Swift/SwiftUI) for primary use; Android available
- Booking flow supports 14 locales (i18n required)

**Core Data Model:**
- **Venue**: multi-tenant root entity; each venue has own floor plans, access rules, staff
- **Guest Profile**: central entity; many-to-many with Venues; stores all 100+ data points
- **Reservation**: linked to Guest Profile, Venue, Table, and Access Rule; stores payment token, status history
- **Table**: linked to Venue; has capacity, section, position (x/y coordinates for floor plan)
- **Access Rule**: defines availability windows, pacing, policies, payment requirements, audiences
- **Auto-tag**: rule definition entity; runs as background job to evaluate and apply tags to profiles
- **Campaign**: linked to Audience Segment (set of tags); stores email/SMS content, trigger rule, performance stats
- **Event/Experience**: inventory entity; linked to Venue; has ticket types, pricing, capacity

**Key Background Jobs:**
- Auto-tag evaluation engine (runs on new data events: reservation created, check-out, feedback received)
- Campaign trigger evaluator (checks tag changes and fires emails/SMS)
- Waitlist pacing engine (updates estimated wait times as floor plan changes)
- Priority Alert dispatcher (monitors cancellations, sends tiered notifications)
- AI feedback aggregator (weekly batch job)

**Integrations Architecture:**
- POS sync: webhook-based (POS posts table/check events to SevenRooms) or polling API
- Google/Facebook: OAuth-based channel integrations; availability feed pushed via API
- Twilio: SMS gateway (A2P 10DLC for US; international shortcode/longcode)
- Payment: Stripe Connect (platform model, operator as connected account) for multi-venue

**Reporting:**
- Reporting API exposed for ETL to external data warehouses
- Internal analytics likely built on a separate OLAP store (not transactional DB)
- Reports scheduled via CRON and delivered via email with CSV attachment or inline view