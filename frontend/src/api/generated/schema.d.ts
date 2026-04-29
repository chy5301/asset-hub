export interface paths {
    "/api/types": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Types */
        get: operations["list_types_api_types_get"];
        put?: never;
        /** Create Type */
        post: operations["create_type_api_types_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/types/{type_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Type */
        get: operations["get_type_api_types__type_id__get"];
        put?: never;
        post?: never;
        /** Delete Type */
        delete: operations["delete_type_api_types__type_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Assets */
        get: operations["list_assets_api_assets_get"];
        put?: never;
        /** Create Asset */
        post: operations["create_asset_api_assets_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/{asset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Asset */
        get: operations["get_asset_api_assets__asset_id__get"];
        put?: never;
        post?: never;
        /**
         * Delete Asset
         * @description 删除资产 cascade（CheckoutRecord + Attachment FS+DB）。
         */
        delete: operations["delete_asset_api_assets__asset_id__delete"];
        options?: never;
        head?: never;
        /**
         * Update Asset
         * @description 整合编辑 + 状态切换。
         *
         *     status 字段由 service 层 state_machine 校验合法性，非法转换抛 ValidationError → 422。
         */
        patch: operations["update_asset_api_assets__asset_id__patch"];
        trace?: never;
    };
    "/api/assets/{asset_id}/checkout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Checkout Asset */
        post: operations["checkout_asset_api_assets__asset_id__checkout_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/{asset_id}/return": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Return Asset */
        post: operations["return_asset_api_assets__asset_id__return_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/{asset_id}/history": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Asset History */
        get: operations["asset_history_api_assets__asset_id__history_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/assets/{asset_id}/attachments": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Attachments */
        get: operations["list_attachments_api_assets__asset_id__attachments_get"];
        put?: never;
        /** Upload Attachment */
        post: operations["upload_attachment_api_assets__asset_id__attachments_post"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/attachments/{attachment_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Attachment */
        get: operations["get_attachment_api_attachments__attachment_id__get"];
        put?: never;
        post?: never;
        /** Delete Attachment */
        delete: operations["delete_attachment_api_attachments__attachment_id__delete"];
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/attachments/{attachment_id}/content": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Download Attachment */
        get: operations["download_attachment_api_attachments__attachment_id__content_get"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AssetCreate */
        AssetCreate: {
            /** Name */
            name: string;
            /**
             * Type Id
             * Format: uuid
             */
            type_id: string;
            /** Serial Number */
            serial_number?: string | null;
            /** Holder */
            holder?: string | null;
            /** Location */
            location?: string | null;
            /** Notes */
            notes?: string | null;
            /** Custom Data */
            custom_data?: {
                [key: string]: unknown;
            };
            /** Acquired At */
            acquired_at?: string | null;
        };
        /** AssetRead */
        AssetRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Asset Code */
            asset_code: string;
            /** Name */
            name: string;
            /** Serial Number */
            serial_number: string | null;
            /**
             * Type Id
             * Format: uuid
             */
            type_id: string;
            /** Type Name */
            type_name: string | null;
            status: components["schemas"]["AssetStatus"];
            /** Holder */
            holder: string | null;
            /** Location */
            location: string | null;
            /** Notes */
            notes: string | null;
            /** Custom Data */
            custom_data: {
                [key: string]: unknown;
            };
            /** Acquired At */
            acquired_at: string | null;
            /** Current Checkout Id */
            current_checkout_id: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /**
         * AssetStatus
         * @enum {string}
         */
        AssetStatus: "IN_USE" | "IDLE" | "MAINTENANCE" | "RETIRED";
        /**
         * AssetUpdate
         * @description 注意：type_id 不暴露——D9 编辑表单禁改 type；asset_code 也不暴露（系统生成、不允许手改）。
         */
        AssetUpdate: {
            /** Name */
            name?: string | null;
            /** Serial Number */
            serial_number?: string | null;
            status?: components["schemas"]["AssetStatus"] | null;
            /** Holder */
            holder?: string | null;
            /** Location */
            location?: string | null;
            /** Notes */
            notes?: string | null;
            /** Custom Data */
            custom_data?: {
                [key: string]: unknown;
            } | null;
            /** Acquired At */
            acquired_at?: string | null;
        };
        /**
         * AttachmentKind
         * @enum {string}
         */
        AttachmentKind: "photo" | "invoice" | "doc" | "other";
        /** AttachmentRead */
        AttachmentRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            kind: components["schemas"]["AttachmentKind"];
            /** Sha256 */
            sha256: string;
            /** Size */
            size: number;
            /** Mime Type */
            mime_type: string;
            /** Original Name */
            original_name: string;
            /**
             * Uploaded At
             * Format: date-time
             */
            uploaded_at: string;
        };
        /** Body_upload_attachment_api_assets__asset_id__attachments_post */
        Body_upload_attachment_api_assets__asset_id__attachments_post: {
            /** File */
            file: string;
            /** @default other */
            kind: components["schemas"]["AttachmentKind"];
        };
        /** CheckoutCreate */
        CheckoutCreate: {
            /** Holder */
            holder: string;
            /** Location */
            location?: string | null;
            /** Note */
            note?: string | null;
        };
        /** CheckoutRead */
        CheckoutRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            /** Holder */
            holder: string;
            /** Location */
            location: string | null;
            /**
             * Checked Out At
             * Format: date-time
             */
            checked_out_at: string;
            /** Returned At */
            returned_at: string | null;
            /** Checkout Note */
            checkout_note: string | null;
            /** Return Note */
            return_note: string | null;
        };
        /** CheckoutReturn */
        CheckoutReturn: {
            /** Note */
            note?: string | null;
        };
        /**
         * CustomFieldDef
         * @description v1 schema：key + label + type + required + options + 扩展属性。
         *
         *     M2c-3 D2 决议：字段名沿用 M1/M2 的 `key`（与 services/validation.py:8 + 现有 fixtures 一致），
         *     不重命名为 name；spec D2 文案随 plan Task 15 同步使用 `key`（前端 FieldDef 也用 key）。
         */
        CustomFieldDef: {
            /** Key */
            key: string;
            /** Label */
            label?: string | null;
            /** Type */
            type: string;
            /**
             * Required
             * @default false
             */
            required: boolean;
            /** Default */
            default?: string | number | boolean | null;
            /** Placeholder */
            placeholder?: string | null;
            /** Help */
            help?: string | null;
            /** Unit */
            unit?: string | null;
            /** Min */
            min?: number | null;
            /** Max */
            max?: number | null;
            /** Options */
            options?: string[] | null;
            /** Displayas */
            displayAs?: string | null;
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** TypeCreate */
        TypeCreate: {
            /** Name */
            name: string;
            /** Code Prefix */
            code_prefix: string;
            /** Description */
            description?: string | null;
            /**
             * Custom Fields
             * @default []
             */
            custom_fields: components["schemas"]["CustomFieldDef"][];
        };
        /** TypeRead */
        TypeRead: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Name */
            name: string;
            /** Code Prefix */
            code_prefix: string;
            /** Description */
            description: string | null;
            /** Custom Fields */
            custom_fields: components["schemas"]["CustomFieldDef"][];
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** ValidationError */
        ValidationError: {
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
            /** Input */
            input?: unknown;
            /** Context */
            ctx?: Record<string, never>;
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_types_api_types_get: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TypeRead"][];
                };
            };
        };
    };
    create_type_api_types_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TypeCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TypeRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_type_api_types__type_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                type_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TypeRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_type_api_types__type_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                type_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_assets_api_assets_get: {
        parameters: {
            query?: {
                type_id?: string | null;
                status?: components["schemas"]["AssetStatus"] | null;
                holder?: string | null;
                q?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_asset_api_assets_post: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_asset_api_assets__asset_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_asset_api_assets__asset_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_asset_api_assets__asset_id__patch: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["AssetUpdate"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AssetRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    checkout_asset_api_assets__asset_id__checkout_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CheckoutCreate"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CheckoutRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    return_asset_api_assets__asset_id__return_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CheckoutReturn"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CheckoutRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    asset_history_api_assets__asset_id__history_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["CheckoutRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_attachments_api_assets__asset_id__attachments_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentRead"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    upload_attachment_api_assets__asset_id__attachments_post: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "multipart/form-data": components["schemas"]["Body_upload_attachment_api_assets__asset_id__attachments_post"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_attachment_api_attachments__attachment_id__get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AttachmentRead"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    delete_attachment_api_attachments__attachment_id__delete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_attachment_api_attachments__attachment_id__content_get: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                attachment_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": unknown;
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
