/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { AccountUpdatePassword } from '../models/AccountUpdatePassword';
import type { CreateUserModel } from '../models/CreateUserModel';
import type { OtpModel } from '../models/OtpModel';
import type { PublicUserModel } from '../models/PublicUserModel';
import type { UserJtiModel } from '../models/UserJtiModel';
import type { UserLoginSignatureModel } from '../models/UserLoginSignatureModel';
import type { UserModel } from '../models/UserModel';
import type { UserToSignModel } from '../models/UserToSignModel';
import type { WebhookModel } from '../models/WebhookModel';

import type { CancelablePromise } from '../core/CancelablePromise';
import type { BaseHttpRequest } from '../core/BaseHttpRequest';

export class AccountService {

    constructor(public readonly httpRequest: BaseHttpRequest) {}

    /**
     * VerifyEmail
     * Verify email for given account
     * @param email
     * @param emailSecret
     * @returns string Redirect Response
     * @throws ApiError
     */
    public controllersAccountEmailVerifyEmailSecretVerifyEmail(
        email: string,
        emailSecret: string,
    ): CancelablePromise<string> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/controllers/account/{email}/email/verify/{email_secret}',
            path: {
                'email': email,
                'email_secret': emailSecret,
            },
            responseHeader: 'location',
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * ToSign
     * Used to generate a unique code to sign.
     * @param email
     * @returns UserToSignModel Request fulfilled, document follows
     * @throws ApiError
     */
    public controllersAccountEmailToSignToSign(
        email: string,
    ): CancelablePromise<UserToSignModel> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/controllers/account/{email}/to-sign',
            path: {
                'email': email,
            },
            errors: {
                400: `Bad request syntax or unsupported method`,
                404: `Nothing matches the given URI`,
            },
        });
    }

    /**
     * Login
     * Validate signature and OTP code
     * @param captcha
     * @param email
     * @param requestBody
     * @param otp
     * @returns UserJtiModel Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountEmailLoginLogin(
        captcha: string,
        email: string,
        requestBody: UserLoginSignatureModel,
        otp?: (null | string),
    ): CancelablePromise<UserJtiModel> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/{email}/login',
            path: {
                'email': email,
            },
            query: {
                'captcha': captcha,
                'otp': otp,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad request syntax or unsupported method`,
                401: `No permission -- see authorization schemes`,
            },
        });
    }

    /**
     * Public
     * Public KDF details
     * @param email
     * @returns PublicUserModel Request fulfilled, document follows
     * @throws ApiError
     */
    public controllersAccountEmailPublicPublic(
        email: string,
    ): CancelablePromise<PublicUserModel> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/controllers/account/{email}/public',
            path: {
                'email': email,
            },
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * OtpSetup
     * Used to confirm OTP is completed
     * @param otp
     * @returns any Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountOtpSetupOtpSetup(
        otp: string,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/otp/setup',
            query: {
                'otp': otp,
            },
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * ResetOtp
     * Reset OTP
     * @param otp
     * @returns OtpModel Request fulfilled, document follows
     * @throws ApiError
     */
    public controllersAccountOtpResetResetOtp(
        otp: string,
    ): CancelablePromise<OtpModel> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/controllers/account/otp/reset',
            query: {
                'otp': otp,
            },
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * AddWebhook
     * Add a webhook
     * @param requestBody
     * @returns any Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountNotificationsWebhookAddAddWebhook(
        requestBody: WebhookModel,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/notifications/webhook/add',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * RemoveWebhook
     * Remove a webhook
     * @param requestBody
     * @returns void
     * @throws ApiError
     */
    public controllersAccountNotificationsWebhookRemoveRemoveWebhook(
        requestBody: WebhookModel,
    ): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/controllers/account/notifications/webhook/remove',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * RemoveEmail
     * Disable email notification
     * @param requestBody
     * @returns void
     * @throws ApiError
     */
    public controllersAccountNotificationsEmailRemoveRemoveEmail(
        requestBody: 'canary_renewals' | 'canary_subscriptions' | 'survey_submissions',
    ): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/controllers/account/notifications/email/remove',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * AddEmail
     * Enable email notification
     * @param requestBody
     * @returns any Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountNotificationsEmailAddAddEmail(
        requestBody: 'canary_renewals' | 'canary_subscriptions' | 'survey_submissions',
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/notifications/email/add',
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * IpProgressingConsent
     * @returns any Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountPrivacyIpProgressingConsentIpProgressingConsent(): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/privacy/ip-progressing/consent',
        });
    }

    /**
     * IpProgressing
     * @returns void
     * @throws ApiError
     */
    public controllersAccountPrivacyIpProgressingDisallowIpProgressing(): CancelablePromise<void> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/controllers/account/privacy/ip-progressing/disallow',
        });
    }

    /**
     * CreateAccount
     * Create a user account
     * @param captcha
     * @param requestBody
     * @returns any Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountCreateCreateAccount(
        captcha: string,
        requestBody: CreateUserModel,
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/create',
            query: {
                'captcha': captcha,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

    /**
     * JwtInfo
     * Get JWT sub for user
     * @returns string Request fulfilled, document follows
     * @throws ApiError
     */
    public controllersAccountJwtJwtInfo(): CancelablePromise<string> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/controllers/account/jwt',
        });
    }

    /**
     * EmailResend
     * Resends email verification
     * @returns any Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountEmailResendEmailResend(): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/email/resend',
        });
    }

    /**
     * Logout
     * Logout of User account
     * @returns any Request fulfilled, document follows
     * @throws ApiError
     */
    public controllersAccountLogoutLogout(): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'DELETE',
            url: '/controllers/account/logout',
        });
    }

    /**
     * GetMe
     * Get user info
     * @returns UserModel Request fulfilled, document follows
     * @throws ApiError
     */
    public controllersAccountMeGetMe(): CancelablePromise<UserModel> {
        return this.httpRequest.request({
            method: 'GET',
            url: '/controllers/account/me',
        });
    }

    /**
     * PasswordReset
     * Reset password
     * @param requestBody
     * @param otp
     * @returns any Document created, URL follows
     * @throws ApiError
     */
    public controllersAccountPasswordResetPasswordReset(
        requestBody: AccountUpdatePassword,
        otp?: (null | string),
    ): CancelablePromise<any> {
        return this.httpRequest.request({
            method: 'POST',
            url: '/controllers/account/password/reset',
            query: {
                'otp': otp,
            },
            body: requestBody,
            mediaType: 'application/json',
            errors: {
                400: `Bad request syntax or unsupported method`,
            },
        });
    }

}
